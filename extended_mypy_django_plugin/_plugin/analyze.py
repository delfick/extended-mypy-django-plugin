from mypy.nodes import Decorator, FuncDef, OverloadedFuncDef, PlaceholderNode, TypeInfo, Var
from mypy.plugin import AnalyzeTypeContext, ClassDefContext
from mypy.plugins import common
from mypy.semanal import SemanticAnalyzer
from mypy.typeanal import TypeAnalyser
from mypy.types import (
    CallableType,
    Instance,
    Overloaded,
    PlaceholderType,
    ProperType,
    TypeAliasType,
    TypeQuery,
    TypeTranslator,
    TypeVarType,
    UnboundType,
    get_proper_type,
)
from mypy.types import Type as MypyType
from mypy_django_plugin.lib import fullnames
from typing_extensions import assert_never

from . import protocols


class HasDefaultQuerySet(TypeQuery[bool]):
    """
    Find where we have unbound types
    """

    def __init__(self, fullname: str) -> None:
        self.fullname = fullname
        super().__init__(any)

    def visit_instance(self, t: Instance) -> bool:
        if len(t.args) != 1:
            return False

        if (
            protocols.KnownAnnotations.resolve(t.type.fullname)
            is not protocols.KnownAnnotations.DEFAULT_QUERYSET
        ):
            return False

        first_arg = get_proper_type(t.args[0])
        return isinstance(first_arg, Instance) and first_arg.type.fullname == self.fullname


class HasTypeVars(TypeQuery[bool]):
    """
    Find where we have a concrete annotation
    """

    def __init__(self) -> None:
        super().__init__(any)

    def visit_type_var(self, t: TypeVarType) -> bool:
        return True


class DefaultQuerySetReplacer(TypeTranslator):
    def __init__(
        self, ctx: ClassDefContext, fullname: str, model_queryset: TypeInfo | None = None
    ) -> None:
        self.ctx = ctx
        self.fullname = fullname
        self.model_queryset = model_queryset
        self.replaced: bool = False

    def _maybe_target_cls(self, typ: ProperType) -> Instance | None:
        if isinstance(typ, UnboundType):
            analyzed = self.ctx.api.anal_type(typ)
            if analyzed is None:
                return None
            typ = get_proper_type(analyzed)

        if isinstance(typ, TypeVarType):
            upper_bound = get_proper_type(typ.upper_bound)
            if not isinstance(upper_bound, Instance):
                return None

            if upper_bound.type.fullname != self.fullname:
                return None

            typ = upper_bound

        if not isinstance(typ, Instance):
            return None

        if typ.type.fullname != self.fullname:
            return None

        return typ

    def visit_unbound_type(self, t: UnboundType) -> MypyType:
        typ = self.ctx.api.anal_type(t)
        if typ is None:
            return t

        typ = get_proper_type(typ)
        if not isinstance(typ, Instance):
            return t

        if (
            protocols.KnownAnnotations.resolve(typ.type.fullname)
            is not protocols.KnownAnnotations.DEFAULT_QUERYSET
        ):
            return t

        if len(t.args) != 1:
            return t

        if first_arg := self._maybe_target_cls(get_proper_type(t.args[0])):
            self.replaced = True
            if self.model_queryset:
                return Instance(self.model_queryset, [first_arg])

        return t

    def visit_instance(self, t: Instance) -> MypyType:
        instance = get_proper_type(super().visit_instance(t))
        if not isinstance(instance, Instance):
            return instance

        t = instance
        if len(t.args) != 1:
            return t

        if (
            protocols.KnownAnnotations.resolve(t.type.fullname)
            is not protocols.KnownAnnotations.DEFAULT_QUERYSET
        ):
            return t

        if first_arg := self._maybe_target_cls(get_proper_type(t.args[0])):
            self.replaced = True
            if self.model_queryset:
                return Instance(self.model_queryset, [first_arg])

        return t

    def visit_type_alias_type(self, t: TypeAliasType) -> MypyType:
        return t.copy_modified(args=[a.accept(self) for a in t.args])


class DefaultQuerySetImplReplacer(TypeTranslator):
    def __init__(self, *, parent: str, cls: Instance, resolver: protocols.Resolver) -> None:
        self.cls = cls
        self.parent = parent
        self.resolver = resolver

    def visit_instance(self, t: Instance) -> MypyType:
        instance = get_proper_type(super().visit_instance(t))
        if not isinstance(instance, Instance):
            return instance

        t = instance
        if len(t.args) != 1:
            return t

        if t.type.fullname != fullnames.QUERYSET_CLASS_FULLNAME:
            return t

        first_arg = get_proper_type(t.args[0])
        if not isinstance(first_arg, Instance) or first_arg.type.fullname != self.parent:
            return t

        resolved = self.resolver.resolve(protocols.KnownAnnotations.DEFAULT_QUERYSET, self.cls)
        if resolved is None:
            return t

        return resolved

    def visit_type_alias_type(self, t: TypeAliasType) -> MypyType:
        return t.copy_modified(args=[a.accept(self) for a in t.args])


class DefaultQuerySetNodeReplacer:
    """
    I would use mypy.visitor.NodeVisitor but https://github.com/python/mypy/issues/16497
    """

    def __init__(self, replacer: DefaultQuerySetReplacer) -> None:
        self.replacer = replacer

    @property
    def replaced(self) -> bool:
        return self.replacer.replaced

    def accept(self, node: OverloadedFuncDef | FuncDef | Decorator | None) -> None:
        if node is None:
            return

        if isinstance(node, OverloadedFuncDef):
            self.visit_overloaded_func_def(node)
        elif isinstance(node, FuncDef):
            self.visit_func_def(node)
        elif isinstance(node, Decorator):
            self.visit_decorator(node)
        else:
            assert_never(node)

    def visit_overloaded_func_def(self, t: OverloadedFuncDef) -> None:
        for item in t.items:
            self.accept(item)

    def visit_decorator(self, t: Decorator) -> None:
        self.visit_func_def(t.func)
        self.visit_var(t.var)

    def visit_var(self, t: Var) -> None:
        if t.type:
            t_type = get_proper_type(t.type)
            if isinstance(t_type, Overloaded):
                t.type = Overloaded(
                    [
                        item.copy_modified(ret_type=item.ret_type.accept(self.replacer))
                        for item in t_type.items
                    ]
                )
            elif isinstance(t_type, CallableType):
                t.type = t_type.copy_modified(ret_type=t_type.ret_type.accept(self.replacer))

    def visit_func_def(self, t: FuncDef) -> None:
        if t.type:
            t_type = t.type
            if isinstance(t_type, Overloaded):
                t.type = Overloaded(
                    [
                        item.copy_modified(ret_type=item.ret_type.accept(self.replacer))
                        for item in t_type.items
                    ]
                )
            elif isinstance(t_type, CallableType):
                t.type = t_type.copy_modified(ret_type=t_type.ret_type.accept(self.replacer))


class Analyzer:
    def __init__(self, make_resolver: protocols.ResolverMaker) -> None:
        self.make_resolver = make_resolver

    def analyze_type(
        self,
        *,
        ctx: AnalyzeTypeContext,
        annotation: protocols.KnownAnnotations,
        is_abstract_model: protocols.IsAbstractModel,
        plugin_lookup_fully_qualified: protocols.LookupFullyQualified,
    ) -> MypyType:
        """
        We resolve annotations at this point. Unless the type being analyzed involves type vars.

        Resolving type vars requires we wait until we are analyzing method/function calls. Between now
        and then we replace the type with an unbound type that wraps a resolved instance because when we
        can resolve the type vars we can't resolve what the type var actually is!
        """
        args = ctx.type.args
        if len(args) != 1:
            ctx.api.fail("Concrete annotations must contain exactly one argument", ctx.context)
            return ctx.type

        model_type = get_proper_type(ctx.api.analyze_type(args[0]))

        model_fullname_type = model_type
        if isinstance(model_fullname_type, TypeVarType):
            model_fullname_type = get_proper_type(model_fullname_type.upper_bound)

        model_fullname: str = ""
        if isinstance(model_fullname_type, Instance):
            model_fullname = model_fullname_type.type.fullname
        elif isinstance(model_fullname_type, PlaceholderType) and model_fullname_type.fullname:
            model_fullname = model_fullname_type.fullname

        resolver = self.make_resolver(ctx=ctx)

        def ignore_on_abstract_model() -> bool:
            if annotation is not protocols.KnownAnnotations.DEFAULT_QUERYSET:
                return False

            assert isinstance(ctx.api, TypeAnalyser)
            assert isinstance(ctx.api.api, SemanticAnalyzer)
            if ctx.api.api.is_class_scope() and isinstance(ctx.api.api.type, Instance | TypeInfo):
                if isinstance(ctx.api.api.type, Instance):
                    cls_fullname = ctx.api.api.type.type.fullname
                else:
                    cls_fullname = ctx.api.api.type.fullname
                if is_abstract_model(cls_fullname) and model_fullname == cls_fullname:
                    return True
            return False

        if ignore_on_abstract_model():
            # Handled in propagate_default_queryset_returns
            annotation_sym = plugin_lookup_fully_qualified(annotation.value)
            if not annotation_sym:
                ctx.api.fail(
                    f"Failed to lookup annotation symbol: {annotation.value}", ctx.context
                )
                return ctx.type

            if not isinstance(annotation_sym.node, TypeInfo):
                ctx.api.fail(
                    f"Expected to find TypeInfo for annotation: {annotation.value}: {annotation_sym.node}",
                    ctx.context,
                )
                return ctx.type

            return Instance(annotation_sym.node, [model_type])

        if model_type.accept(HasTypeVars()):
            ctx.api.fail(
                "Using a concrete annotation on a TypeVar is not currently supported", ctx.context
            )
            return ctx.type

        resolved = resolver.resolve(annotation, model_type)
        if resolved is None:
            return ctx.type
        else:
            return resolved

    def register_decorated_model(self, ctx: ClassDefContext) -> bool:
        ns = "extended_mypy_django_plugin"
        meta_name = "replaced_default_queryset_methods"
        metadata = ctx.cls.info.metadata
        if ns not in metadata:
            metadata[ns] = {}

        if meta_name not in metadata[ns]:
            metadata[ns][meta_name] = []

        return True

    def ensure_defaultqueryset_decorator(
        self, ctx: ClassDefContext, is_abstract_model: protocols.IsAbstractModel
    ) -> None:
        ns = "extended_mypy_django_plugin"
        meta_name = "replaced_default_queryset_methods"

        parent_is_decorated: str | None = None
        for parent in ctx.cls.info.mro:
            if parent == ctx.cls.info:
                continue
            if parent.fullname == "django.db.models.base.Model":
                continue

            if ns not in parent.metadata:
                continue

            if meta_name not in parent.metadata[ns]:
                continue

            parent_is_decorated = parent.fullname

        is_decorated: bool = False
        metadata = ctx.cls.info.metadata
        if ns in metadata and meta_name in metadata[ns]:
            is_decorated = True

        if parent_is_decorated:
            if not is_decorated:
                ctx.api.fail(
                    f"Parent class '{parent_is_decorated}' has a @Concrete.change_default_queryset_returns decorator, which means so does this class '{ctx.cls.info.fullname}'",
                    ctx.cls,
                )

        if is_abstract_model(ctx.cls.info.fullname):
            for name, node in ctx.cls.info.names.items():
                if "-redefinition" in name:
                    continue

                if node.plugin_generated:
                    continue

                if not isinstance(node.node, OverloadedFuncDef | FuncDef | Decorator):
                    continue

                replacer = DefaultQuerySetNodeReplacer(
                    DefaultQuerySetReplacer(ctx, ctx.cls.info.fullname)
                )
                replacer.accept(node.node)
                if replacer.replaced and not is_decorated:
                    ctx.api.fail(
                        "Abstract models that return DefaultQuerySet[Model] should be decorated with @Concrete.Concrete.change_default_queryset_returns",
                        ctx.cls,
                    )
                    return

    def propagate_default_queryset_returns(
        self, ctx: ClassDefContext, is_abstract_model: protocols.IsAbstractModel
    ) -> bool:
        metadata = ctx.cls.info.metadata

        ns = "extended_mypy_django_plugin"
        meta_name = "replaced_default_queryset_methods"

        model_queryset_sym = ctx.api.lookup_fully_qualified(fullnames.QUERYSET_CLASS_FULLNAME)
        if model_queryset_sym is None:
            ctx.api.fail(
                f"Failed to lookup symbol for django queryset class {fullnames.QUERYSET_CLASS_FULLNAME}",
                ctx.cls,
            )
            return True

        if isinstance(model_queryset_sym.node, PlaceholderNode):
            if not ctx.api.final_iteration:
                ctx.api.defer()
                return False

        if not isinstance(model_queryset_sym.node, TypeInfo):
            ctx.api.fail(
                f"Expected TypeInfo associated with django queryset class {fullnames.QUERYSET_CLASS_FULLNAME}: {model_queryset_sym.node}",
                ctx.cls,
            )
            return True

        relevant_parents: dict[str, TypeInfo] = {}
        for parent in ctx.cls.info.mro:
            if parent == ctx.cls.info:
                continue
            if parent.fullname == "django.db.models.base.Model":
                continue

            if ns not in parent.metadata:
                continue

            if meta_name not in parent.metadata[ns]:
                continue

            for name in parent.metadata[ns][meta_name]:
                if name not in ctx.cls.info.names and name not in relevant_parents:
                    relevant_parents[name] = parent

        if is_abstract_model(ctx.cls.info.fullname):
            if ns not in metadata:
                metadata[ns] = {}
            if not isinstance(metadata[ns].get(meta_name), list):
                metadata[ns][meta_name] = []

            replaced_default_queryset_methods: list[str] = []
            for name, node in ctx.cls.info.names.items():
                if "-redefinition" in name:
                    continue

                if node.plugin_generated:
                    continue

                if not isinstance(node.node, OverloadedFuncDef | FuncDef | Decorator):
                    continue

                replacer = DefaultQuerySetNodeReplacer(
                    DefaultQuerySetReplacer(ctx, ctx.cls.info.fullname, model_queryset_sym.node)
                )
                replacer.accept(node.node)
                if replacer.replaced:
                    if isinstance(node.node, OverloadedFuncDef):
                        ctx.api.fail(
                            "Don't support DefaultQuerySet[Model] inside overloaded functions",
                            ctx.cls,
                        )
                        continue
                    replaced_default_queryset_methods.append(name)

            metadata[ns][meta_name] = replaced_default_queryset_methods

        if relevant_parents and not is_abstract_model(ctx.cls.info.fullname):
            resolver = self.make_resolver(ctx=ctx)
            for name, parent in relevant_parents.items():
                on_parent = parent.names[name].node
                is_classmethod = False
                is_staticmethod = False
                if isinstance(on_parent, Decorator):
                    is_classmethod = on_parent.var.is_classmethod
                    is_staticmethod = on_parent.var.is_staticmethod
                    arguments = on_parent.func.arguments
                    callable_type = on_parent.func.type
                elif isinstance(on_parent, FuncDef):
                    arguments = on_parent.arguments
                    callable_type = on_parent.type
                else:
                    ctx.api.fail(f"Expected a FuncDef or decorator, got {on_parent}", ctx.cls)
                    continue

                if not isinstance(callable_type, CallableType):
                    ctx.api.fail(f"Expected a CallableType, got {callable_type}", ctx.cls)
                    continue

                impl_replacer = DefaultQuerySetImplReplacer(
                    parent=parent.fullname, cls=Instance(ctx.cls.info, []), resolver=resolver
                )

                common.add_method_to_class(
                    ctx.api,
                    ctx.cls,
                    name,
                    # Don't include self/cls
                    arguments[1:],
                    callable_type.ret_type.accept(impl_replacer),
                    is_classmethod=is_classmethod,
                    is_staticmethod=is_staticmethod,
                )

        return True
