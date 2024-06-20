from mypy.nodes import (
    GDEF,
    AssignmentStmt,
    CastExpr,
    NameExpr,
    StrExpr,
    SymbolTableNode,
    TypeInfo,
    Var,
)
from mypy.plugin import (
    AnalyzeTypeContext,
    DynamicClassDefContext,
    SemanticAnalyzerPluginInterface,
    TypeAnalyzerPluginInterface,
)
from mypy.semanal import SemanticAnalyzer
from mypy.types import (
    CallableType,
    Instance,
    TypeType,
    TypeVarType,
    UnionType,
    get_proper_type,
)
from mypy.types import Type as MypyType

from . import protocols


class TypeAnalyzer:
    def __init__(self, resolver: protocols.Resolver, api: TypeAnalyzerPluginInterface) -> None:
        self.api = api
        self.resolver = resolver

    def analyze(self, ctx: AnalyzeTypeContext, annotation: protocols.KnownAnnotations) -> MypyType:
        type_arg, rewrap = self.resolver.find_type_arg(ctx.type, self.api.analyze_type)
        if type_arg is None:
            return ctx.type

        if rewrap:
            return self.resolver.rewrap_type_var(
                type_arg=type_arg, annotation=annotation, default=ctx.type
            )

        resolved = self.resolver.resolve(annotation, type_arg)
        if resolved is None:
            return ctx.type
        else:
            return resolved


class SemAnalyzing:
    def __init__(
        self, *, resolver: protocols.Resolver, api: SemanticAnalyzerPluginInterface
    ) -> None:
        # We need much more than is on the interface unfortunately
        assert isinstance(api, SemanticAnalyzer)
        self.api = api
        self.resolver = resolver

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

        concrete = self.resolver.resolve(
            protocols.KnownAnnotations.CONCRETE,
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
        if len(ctx.call.args) != 2:
            self.api.fail("Concrete.type_var takes exactly two arguments", ctx.call)
            return None

        name = self.api.extract_typevarlike_name(
            AssignmentStmt([NameExpr(ctx.name)], ctx.call.callee), ctx.call
        )
        if name is None:
            return None

        second_arg = ctx.call.args[1]
        model_name: str

        if isinstance(second_arg, StrExpr):
            if second_arg.value.isidentifier():
                model_name = f"{self.api.cur_mod_id}.{second_arg.value}"
            else:
                self.api.fail(
                    "Concrete.type_var needs to take the instance or name of a model class in this file",
                    ctx.call,
                )
                return None
        elif isinstance(second_arg, NameExpr):
            model_name = f"{self.api.cur_mod_id}.{second_arg.name}"
        else:
            self.api.fail(
                "Second argument to type_var must be either a simple name or a string of the name",
                ctx.call,
            )

        parent = self.api.lookup_fully_qualified_or_none(model_name)

        if parent is None:
            if self.api.final_iteration:
                self.api.fail(
                    f"Failed to locate the model provided to to make {ctx.name} ({model_name})",
                    ctx.call,
                )
                return None
            else:
                self.api.defer()
                return None

        if not isinstance(parent.node, TypeInfo):
            self.api.fail(
                "Second argument to Concrete.type_var was not pointing at a class", ctx.call
            )
            return

        type_var_expr = self.resolver.type_var_expr_for(
            model=parent.node,
            name=name,
            fullname=f"{self.api.cur_mod_id}.{name}",
            object_type=self.api.named_type("builtins.object"),
        )

        module = self.api.modules[self.api.cur_mod_id]
        module.names[name] = SymbolTableNode(GDEF, type_var_expr, plugin_generated=True)
        return None
