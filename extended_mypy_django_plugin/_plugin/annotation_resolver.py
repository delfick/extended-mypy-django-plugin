import functools
from collections.abc import Iterator, Sequence
from typing import TYPE_CHECKING, cast

from mypy.nodes import Context, PlaceholderNode, TypeAlias, TypeInfo, TypeVarExpr
from mypy.plugin import (
    AnalyzeTypeContext,
    AttributeContext,
    DynamicClassDefContext,
    FunctionContext,
    FunctionSigContext,
    MethodContext,
    MethodSigContext,
)
from mypy.semanal import SemanticAnalyzer
from mypy.typeanal import TypeAnalyser
from mypy.types import (
    AnyType,
    Instance,
    ProperType,
    TypeOfAny,
    TypeType,
    TypeVarType,
    UnboundType,
    UnionType,
    get_proper_type,
)
from mypy.types import Type as MypyType
from typing_extensions import Self, assert_never

from . import protocols


class ShouldDefer(Exception):
    pass


class AnnotationResolver:
    @classmethod
    def create(
        cls,
        *,
        get_concrete_aliases: protocols.AliasGetter,
        get_queryset_aliases: protocols.AliasGetter,
        plugin_lookup_fully_qualified: protocols.LookupFullyQualified,
        ctx: protocols.ValidContextForAnnotationResolver,
    ) -> Self:
        def sem_defer(sem_api: SemanticAnalyzer) -> bool:
            if sem_api.final_iteration:
                return True
            else:
                sem_api.defer()
                return False

        def _lookup_info(sem_api: SemanticAnalyzer | None, fullname: str) -> TypeInfo | None:
            if sem_api is not None:
                instance = sem_api.named_type_or_none(fullname)
                if instance:
                    return instance.type

            sym = plugin_lookup_fully_qualified(fullname)
            if not sym or not isinstance(node := sym.node, TypeInfo):
                return None
            else:
                return node

        def checker_named_type_or_none(
            fullname: str, args: list[MypyType] | None = None
        ) -> Instance | None:
            sym = plugin_lookup_fully_qualified(fullname)
            if not sym or not isinstance(node := sym.node, TypeInfo):
                return None
            if args:
                return Instance(node, args)
            return Instance(node, [AnyType(TypeOfAny.special_form)] * len(node.defn.type_vars))

        def lookup_alias(alias: str) -> Iterator[Instance]:
            sym = plugin_lookup_fully_qualified(alias)
            if sym and isinstance(sym.node, PlaceholderNode):
                raise ShouldDefer()
            assert sym and isinstance(sym.node, TypeAlias)
            target = get_proper_type(sym.node.target)

            if isinstance(target, Instance):
                yield target
            elif isinstance(target, UnionType):
                for item in target.items:
                    found = get_proper_type(item)
                    assert isinstance(found, Instance)
                    yield found
            else:
                raise AssertionError(f"Expected only instances or unions, got {target}")

        fail: protocols.FailFunc
        defer: protocols.DeferFunc
        context: Context
        lookup_info: protocols.LookupInfo
        named_type_or_none: protocols.NamedTypeOrNone

        match ctx:
            case DynamicClassDefContext(api=api):
                assert isinstance(api, SemanticAnalyzer)
                context = ctx.call
                sem_api = api
                defer = functools.partial(sem_defer, sem_api)
                fail = functools.partial(sem_api.fail, ctx=context)
                lookup_info = functools.partial(_lookup_info, sem_api)
                named_type_or_none = sem_api.named_type_or_none
            case AnalyzeTypeContext(api=api):
                assert isinstance(api, TypeAnalyser)
                assert isinstance(api.api, SemanticAnalyzer)
                context = ctx.context
                sem_api = api.api
                defer = functools.partial(sem_defer, sem_api)
                fail = functools.partial(sem_api.fail, ctx=context)
                lookup_info = functools.partial(_lookup_info, sem_api)
                named_type_or_none = sem_api.named_type_or_none
            case (
                AttributeContext(api=api)
                | MethodContext(api=api)
                | FunctionContext(api=api)
                | MethodSigContext(api=api)
                | FunctionSigContext(api=api)
            ):
                context = ctx.context
                defer = lambda: True
                # The interface for the type checker says fail takes ctx
                # But the implementation of TypeChecker has it as context
                fail = functools.partial(api.fail, context=context)
                lookup_info = functools.partial(_lookup_info, None)
                named_type_or_none = checker_named_type_or_none
            case _:
                assert_never(ctx)

        return cls(
            context=context,
            get_concrete_aliases=get_concrete_aliases,
            get_queryset_aliases=get_queryset_aliases,
            defer=defer,
            fail=fail,
            lookup_info=lookup_info,
            lookup_alias=lookup_alias,
            named_type_or_none=named_type_or_none,
        )

    def __init__(
        self,
        *,
        context: Context,
        get_concrete_aliases: protocols.AliasGetter,
        get_queryset_aliases: protocols.AliasGetter,
        fail: protocols.FailFunc,
        defer: protocols.DeferFunc,
        lookup_alias: protocols.LookupAlias,
        lookup_info: protocols.LookupInfo,
        named_type_or_none: protocols.NamedTypeOrNone,
    ) -> None:
        self._defer = defer
        self._named_type_or_none = named_type_or_none
        self.fail = fail
        self.context = context
        self.lookup_info = lookup_info
        self.lookup_alias = lookup_alias
        self.get_concrete_aliases = get_concrete_aliases
        self.get_queryset_aliases = get_queryset_aliases

    def _flatten_union(self, typ: ProperType) -> Iterator[ProperType]:
        if isinstance(typ, UnionType):
            for item in typ.items:
                yield from self._flatten_union(get_proper_type(item))
        else:
            yield typ

    def _analyze_first_type_arg(
        self, type_arg: ProperType, get_aliases: protocols.AliasGetter
    ) -> tuple[bool, Sequence[Instance] | None]:
        is_type: bool = False

        found: ProperType = type_arg
        if isinstance(type_arg, TypeType):
            is_type = True
            found = type_arg.item

        if isinstance(found, AnyType):
            self.fail("Tried to use concrete annotations on a typing.Any")
            return False, None

        if not isinstance(found, Instance | UnionType):
            return False, None

        if isinstance(found, Instance):
            found = UnionType((found,))

        all_types = list(self._flatten_union(found))
        all_instances: list[Instance] = []
        not_all_instances: bool = False
        for item in all_types:
            if not isinstance(item, Instance):
                self.fail(
                    f"Expected to operate on specific classes, got a {item.__class__.__name__}: {item}"
                )
                not_all_instances = True
            else:
                all_instances.append(item)

        if not_all_instances:
            return False, None

        concrete: list[Instance] = []
        names = ", ".join([item.type.fullname for item in all_instances])

        for item in all_instances:
            concrete.extend(list(self.instances_from_aliases(get_aliases, item.type.fullname)))

        if not concrete:
            if not self._defer():
                self.fail(f"No concrete models found for {names}")
            return False, None

        return is_type, tuple(concrete)

    def _make_union(
        self, is_type: bool, instances: Sequence[Instance]
    ) -> UnionType | Instance | TypeType:
        items: Sequence[UnionType | TypeType | Instance]

        if is_type:
            items = [item if isinstance(item, TypeType) else TypeType(item) for item in instances]
        else:
            items = instances

        if len(items) == 1:
            return items[0]
        else:
            return UnionType(tuple(items))

    def _has_typevars(self, type_arg: ProperType) -> bool:
        if isinstance(type_arg, TypeType):
            type_arg = type_arg.item

        if isinstance(type_arg, TypeVarType):
            return True

        if not isinstance(type_arg, UnionType):
            return False

        return any(self._has_typevars(get_proper_type(item)) for item in type_arg.items)

    def resolve(
        self, annotation: protocols.KnownAnnotations, type_arg: ProperType
    ) -> Instance | TypeType | UnionType | AnyType | None:
        if annotation is protocols.KnownAnnotations.CONCRETE:
            return self.find_concrete_models(type_arg)
        elif annotation is protocols.KnownAnnotations.DEFAULT_QUERYSET:
            return self.find_default_queryset(type_arg)
        else:
            assert_never(annotation)

    def find_type_arg(
        self, unbound_type: UnboundType, analyze_type: protocols.TypeAnalyze
    ) -> tuple[ProperType | None, bool]:
        args = unbound_type.args
        if len(args := unbound_type.args) != 1:
            self.fail("Concrete annotations must contain exactly one argument")
            return None, False

        type_arg = get_proper_type(analyze_type(args[0]))
        needs_rewrap = self._has_typevars(type_arg)
        return type_arg, needs_rewrap

    def type_var_expr_for(
        self, *, model: TypeInfo, name: str, fullname: str, object_type: Instance
    ) -> TypeVarExpr:
        try:
            values = list(self.instances_from_aliases(self.get_concrete_aliases, model.fullname))
        except ShouldDefer:
            values = []
        else:
            if not values:
                self.fail(f"No concrete children found for {model.fullname}")

        return TypeVarExpr(
            name=name,
            fullname=fullname,
            values=list(values),
            upper_bound=object_type,
            default=AnyType(TypeOfAny.from_omitted_generics),
        )

    def rewrap_type_var(
        self,
        *,
        annotation: protocols.KnownAnnotations,
        type_arg: ProperType,
        default: MypyType,
    ) -> MypyType:
        info = self.lookup_info(annotation.value)
        if info is None:
            self.fail(f"Couldn't find information for {annotation.value}")
            return default

        if isinstance(type_arg, TypeType) and isinstance(type_arg.item, TypeVarType):
            if type_arg.item.fullname == "extended_mypy_django_plugin.annotations.T_Parent":
                return default
        elif isinstance(type_arg, TypeVarType):
            if type_arg.fullname == "extended_mypy_django_plugin.annotations.T_Parent":
                return default

        return UnboundType(
            "__ConcreteWithTypeVar__",
            [Instance(info, [type_arg])],
            line=self.context.line,
            column=self.context.column,
        )

    def instances_from_aliases(
        self, get_aliases: protocols.AliasGetter, *models: str
    ) -> Iterator[Instance]:
        for model, alias in get_aliases(*models).items():
            if alias is None:
                self.fail(f"Failed to find concrete alias instance for '{model}'")
                continue

            try:
                yield from self.lookup_alias(alias)
            except AssertionError:
                self.fail(f"Failed to create concrete alias instance for '{model}' ({alias})")

    def find_concrete_models(
        self, type_arg: ProperType
    ) -> Instance | TypeType | UnionType | AnyType | None:
        is_type, concrete = self._analyze_first_type_arg(type_arg, self.get_concrete_aliases)
        if concrete is None:
            return None

        return self._make_union(is_type, concrete)

    def find_default_queryset(
        self, type_arg: ProperType
    ) -> Instance | TypeType | UnionType | AnyType | None:
        is_type, concrete = self._analyze_first_type_arg(type_arg, self.get_queryset_aliases)
        if concrete is None:
            return None

        return self._make_union(is_type, concrete)


make_resolver = AnnotationResolver.create

if TYPE_CHECKING:
    _R: protocols.Resolver = cast(AnnotationResolver, None)
