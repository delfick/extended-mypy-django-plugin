from mypy.nodes import (
    GDEF,
    CastExpr,
    StrExpr,
    SymbolTableNode,
    TypeInfo,
    TypeVarExpr,
    Var,
)
from mypy.plugin import AnalyzeTypeContext, DynamicClassDefContext
from mypy.semanal import SemanticAnalyzer
from mypy.typeanal import TypeAnalyser
from mypy.types import (
    AnyType,
    CallableType,
    Instance,
    TypeOfAny,
    TypeType,
    TypeVarType,
    UnionType,
    get_proper_type,
)
from mypy.types import (
    Type as MypyType,
)

from .. import _known_annotations, _store
from . import _annotation_resolver


class TypeAnalyzer:
    def __init__(self, store: _store.Store, api: TypeAnalyser, sem_api: SemanticAnalyzer) -> None:
        self.api = api
        self.store = store
        self.sem_api = sem_api

    def _lookup_info(self, fullname: str) -> TypeInfo | None:
        instance = self.sem_api.named_type_or_none(fullname)
        if instance:
            return instance.type

        return self.store.plugin_lookup_info(fullname)

    def analyze(
        self, ctx: AnalyzeTypeContext, annotation: _known_annotations.KnownAnnotations
    ) -> MypyType:
        def defer() -> bool:
            if self.sem_api.final_iteration:
                return True
            else:
                self.sem_api.defer()
                return False

        resolver = _annotation_resolver.AnnotationResolver(
            self.store,
            defer=defer,
            fail=lambda msg: self.api.fail(msg, ctx.context),
            lookup_info=self._lookup_info,
            named_type_or_none=self.sem_api.named_type_or_none,
        )

        type_arg = resolver.find_type_arg(ctx.type, self.api.analyze_type)
        if type_arg is None:
            return ctx.type

        result = resolver.resolve(annotation, type_arg)
        if result is None:
            return ctx.type
        else:
            return result


class SemAnalyzing:
    def __init__(self, store: _store.Store, *, api: SemanticAnalyzer) -> None:
        self.api = api
        self.store = store

    def _lookup_info(self, fullname: str) -> TypeInfo | None:
        instance = self.api.named_type_or_none(fullname)
        if instance:
            return instance.type

        return self.store.plugin_lookup_info(fullname)

    def transform_cast_as_concrete(self, ctx: DynamicClassDefContext) -> None:
        if len(ctx.call.args) != 1:
            self.api.fail("Concrete.cast_as_concrete takes exactly one argument", ctx.call)
            return None

        node = self.api.lookup_type_node(ctx.call.args[0])
        if not node or not node.node:
            self.api.fail("Failed to lookup the argument", ctx.call)
            return None

        arg_node = self.api.lookup_current_scope(node.node.name)

        if arg_node is None or arg_node.type is None or arg_node.node is None:
            return None

        if not isinstance(arg_node.node, Var):
            return None

        arg_node_typ = get_proper_type(arg_node.type)

        is_type: bool = False
        if isinstance(arg_node_typ, TypeType):
            is_type = True
            arg_node_typ = arg_node_typ.item

        if not isinstance(arg_node_typ, Instance | UnionType | TypeVarType):
            self.api.fail(
                f"Unsure what to do with the type of the argument given to cast_as_concrete: {arg_node_typ}",
                ctx.call,
            )
            return None

        if isinstance(arg_node_typ, TypeVarType):
            if (
                self.api.is_func_scope()
                and isinstance(self.api.type, TypeInfo)
                and arg_node_typ.name == "Self"
            ):
                replacement: Instance | TypeType | None = self.api.named_type_or_none(
                    self.api.type.fullname
                )
                if replacement:
                    arg_node_typ = replacement
                    if is_type:
                        replacement = TypeType(replacement)

                    if self.api.scope.function and isinstance(
                        self.api.scope.function.type, CallableType
                    ):
                        if self.api.scope.function.type.arg_names[0] == ctx.name:
                            # Avoid getting an assignment error trying to assign a union of the concrete types to
                            # a variable typed in terms of Self
                            self.api.scope.function.type.arg_types[0] = replacement
                else:
                    self.api.fail("Failed to resolve Self", ctx.call)
                    return None
            else:
                self.api.fail(
                    f"Resolving type variables for cast_as_concrete not implemented: {arg_node_typ}",
                    ctx.call,
                )
                return None

        def defer() -> bool:
            if self.api.final_iteration:
                return True
            else:
                self.api.defer()
                return False

        resolver = _annotation_resolver.AnnotationResolver(
            self.store,
            defer=defer,
            fail=lambda msg: self.api.fail(msg, ctx.call),
            lookup_info=self._lookup_info,
            named_type_or_none=self.api.named_type_or_none,
        )

        concrete = resolver.resolve(
            _known_annotations.KnownAnnotations.CONCRETE,
            TypeType(arg_node_typ) if is_type else arg_node_typ,
        )
        if not concrete:
            return None

        ctx.call.analyzed = CastExpr(ctx.call.args[0], concrete)
        ctx.call.analyzed.line = ctx.call.line
        ctx.call.analyzed.column = ctx.call.column
        ctx.call.analyzed.accept(self.api)

        return None

    def transform_type_var_classmethod(self, ctx: DynamicClassDefContext) -> None:
        if not isinstance(ctx.call.args[0], StrExpr):
            self.api.fail(
                "First argument to Concrete.type_var must be a string of the name of the variable",
                ctx.call,
            )
            return

        name = ctx.call.args[0].value
        if name != ctx.name:
            self.api.fail(
                f"First argument {name} was not the name of the variable {ctx.name}",
                ctx.call,
            )
            return

        module = self.api.modules[self.api.cur_mod_id]
        if isinstance(module.names.get(name), TypeVarType):
            return

        parent: SymbolTableNode | None = None
        try:
            parent = self.api.lookup_type_node(ctx.call.args[1])
        except AssertionError:
            parent = None

        if parent is None:
            self.api.fail(
                "Second argument to Concrete.type_var must be the abstract model class to find concrete instances of",
                ctx.call,
            )
            return

        if not isinstance(parent.node, TypeInfo):
            self.api.fail(
                "Second argument to Concrete.type_var was not pointing at a class", ctx.call
            )
            return

        object_type = self.api.named_type("builtins.object")
        values = self.store.retrieve_concrete_children_types(
            parent.node, self._lookup_info, self.api.named_type_or_none
        )
        if not values:
            self.api.fail(f"No concrete children found for {parent.node.fullname}", ctx.call)

        type_var_expr = TypeVarExpr(
            name=name,
            fullname=f"{self.api.cur_mod_id}.{name}",
            values=list(values),
            upper_bound=object_type,
            default=AnyType(TypeOfAny.from_omitted_generics),
        )

        module.names[name] = SymbolTableNode(GDEF, type_var_expr, plugin_generated=True)
        return None
