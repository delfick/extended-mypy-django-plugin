import functools
from collections.abc import Iterator, Sequence
from typing import Protocol

from mypy.nodes import Context, TypeInfo, TypeVarExpr
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

from .. import _known_annotations


class FailFunc(Protocol):
    def __call__(self, msg: str) -> None: ...


class DeferFunc(Protocol):
    def __call__(self) -> bool: ...


class TypeAnalyze(Protocol):
    def __call__(self, typ: MypyType, /) -> MypyType: ...


class LookupInfo(Protocol):
    def __call__(self, fullname: str) -> TypeInfo | None: ...


class LookupInstanceFunction(Protocol):
    def __call__(self, fullname: str) -> Instance | None: ...


class NamedTypeOrNone(Protocol):
    def __call__(self, fullname: str, args: list[MypyType] | None = None) -> Instance | None: ...


class ConcreteChildrenTypesRetriever(Protocol):
    def __call__(
        self,
        parent: TypeInfo,
        lookup_info: LookupInfo,
        lookup_instance: LookupInstanceFunction,
    ) -> Sequence[Instance]: ...


class QuerysetRealiser(Protocol):
    def __call__(
        self, type_var: Instance | UnionType, lookup_info: LookupInfo
    ) -> Iterator[Instance]: ...


ValidContextForAnnotationResolver = (
    DynamicClassDefContext
    | AnalyzeTypeContext
    | AttributeContext
    | MethodContext
    | MethodSigContext
    | FunctionContext
    | FunctionSigContext
)


class Resolver(Protocol):
    @property
    def fail(self) -> FailFunc: ...

    def resolve(
        self, annotation: _known_annotations.KnownAnnotations, type_arg: ProperType
    ) -> Instance | TypeType | UnionType | AnyType | None: ...

    def find_type_arg(
        self, unbound_type: UnboundType, analyze_type: TypeAnalyze
    ) -> tuple[ProperType | None, bool]: ...

    def rewrap_type_var(
        self,
        *,
        annotation: _known_annotations.KnownAnnotations,
        type_arg: ProperType,
        default: MypyType,
    ) -> MypyType: ...

    def type_var_expr_for(
        self, *, model: TypeInfo, name: str, fullname: str, object_type: Instance
    ) -> TypeVarExpr: ...


class AnnotationResolver:
    @classmethod
    def create(
        cls,
        *,
        retrieve_concrete_children_types: ConcreteChildrenTypesRetriever,
        realise_querysets: QuerysetRealiser,
        plugin_lookup_info: LookupInfo,
        ctx: ValidContextForAnnotationResolver,
    ) -> Self:
        def sem_defer(sem_api: SemanticAnalyzer) -> bool:
            if sem_api.final_iteration:
                return True
            else:
                sem_api.defer()
                return False

        def sem_lookup_info(sem_api: SemanticAnalyzer, fullname: str) -> TypeInfo | None:
            instance = sem_api.named_type_or_none(fullname)
            if instance:
                return instance.type

            return plugin_lookup_info(fullname)

        def checker_named_type_or_none(
            fullname: str, args: list[MypyType] | None = None
        ) -> Instance | None:
            node = plugin_lookup_info(fullname)
            if not isinstance(node, TypeInfo):
                return None
            if args:
                return Instance(node, args)
            return Instance(node, [AnyType(TypeOfAny.special_form)] * len(node.defn.type_vars))

        fail: FailFunc
        defer: DeferFunc
        context: Context
        lookup_info: LookupInfo
        named_type_or_none: NamedTypeOrNone

        match ctx:
            case DynamicClassDefContext(api=api):
                assert isinstance(api, SemanticAnalyzer)
                context = ctx.call
                sem_api = api
                defer = functools.partial(sem_defer, sem_api)
                fail = lambda msg: sem_api.fail(msg, context)
                lookup_info = functools.partial(sem_lookup_info, sem_api)
                named_type_or_none = sem_api.named_type_or_none
            case AnalyzeTypeContext(api=api):
                assert isinstance(api, TypeAnalyser)
                assert isinstance(api.api, SemanticAnalyzer)
                context = ctx.context
                sem_api = api.api
                defer = functools.partial(sem_defer, sem_api)
                fail = lambda msg: sem_api.fail(msg, context)
                lookup_info = functools.partial(sem_lookup_info, sem_api)
                named_type_or_none = sem_api.named_type_or_none
            case MethodContext(api=api):
                context = ctx.context
                defer = lambda: True
                fail = lambda msg: api.fail(msg, context)
                lookup_info = plugin_lookup_info
                named_type_or_none = checker_named_type_or_none
            case FunctionContext(api=api):
                context = ctx.context
                defer = lambda: True
                fail = lambda msg: api.fail(msg, context)
                lookup_info = plugin_lookup_info
                named_type_or_none = checker_named_type_or_none
            case MethodSigContext(api=api):
                context = ctx.context
                defer = lambda: True
                fail = lambda msg: api.fail(msg, context)
                lookup_info = plugin_lookup_info
                named_type_or_none = checker_named_type_or_none
            case FunctionSigContext(api=api):
                context = ctx.context
                defer = lambda: True
                fail = lambda msg: api.fail(msg, context)
                lookup_info = plugin_lookup_info
                named_type_or_none = checker_named_type_or_none
            case AttributeContext(api=api):
                context = ctx.context
                defer = lambda: True
                fail = lambda msg: api.fail(msg, context)
                lookup_info = plugin_lookup_info
                named_type_or_none = checker_named_type_or_none
            case _:
                assert_never(ctx)

        return cls(
            context=context,
            retrieve_concrete_children_types=retrieve_concrete_children_types,
            realise_querysets=realise_querysets,
            defer=defer,
            fail=fail,
            lookup_info=lookup_info,
            named_type_or_none=named_type_or_none,
        )

    def __init__(
        self,
        *,
        context: Context,
        realise_querysets: QuerysetRealiser,
        retrieve_concrete_children_types: ConcreteChildrenTypesRetriever,
        fail: FailFunc,
        defer: DeferFunc,
        lookup_info: LookupInfo,
        named_type_or_none: NamedTypeOrNone,
    ) -> None:
        self._defer = defer
        self._named_type_or_none = named_type_or_none
        self.fail = fail
        self.context = context
        self.lookup_info = lookup_info
        self.realise_querysets = realise_querysets
        self.retrieve_concrete_children_types = retrieve_concrete_children_types

    def _flatten_union(self, typ: ProperType) -> Iterator[ProperType]:
        if isinstance(typ, UnionType):
            for item in typ.items:
                yield from self._flatten_union(get_proper_type(item))
        else:
            yield typ

    def _analyze_first_type_arg(
        self, type_arg: ProperType
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
            concrete.extend(
                self.retrieve_concrete_children_types(
                    item.type, self.lookup_info, self._named_type_or_none
                )
            )

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

    def resolve(
        self, annotation: _known_annotations.KnownAnnotations, type_arg: ProperType
    ) -> Instance | TypeType | UnionType | AnyType | None:
        if annotation is _known_annotations.KnownAnnotations.CONCRETE:
            return self.find_concrete_models(type_arg)
        elif annotation is _known_annotations.KnownAnnotations.DEFAULT_QUERYSET:
            return self.find_default_queryset(type_arg)
        else:
            assert_never(annotation)

    def find_type_arg(
        self, unbound_type: UnboundType, analyze_type: TypeAnalyze
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
        values = self.retrieve_concrete_children_types(
            model, self.lookup_info, self._named_type_or_none
        )
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
        annotation: _known_annotations.KnownAnnotations,
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

    def _has_typevars(self, type_arg: ProperType) -> bool:
        if isinstance(type_arg, TypeType):
            type_arg = type_arg.item

        if isinstance(type_arg, TypeVarType):
            return True

        if not isinstance(type_arg, UnionType):
            return False

        return any(self._has_typevars(get_proper_type(item)) for item in type_arg.items)

    def find_concrete_models(
        self, type_arg: ProperType
    ) -> Instance | TypeType | UnionType | AnyType | None:
        is_type, concrete = self._analyze_first_type_arg(type_arg)
        if concrete is None:
            return None

        return self._make_union(is_type, concrete)

    def find_default_queryset(
        self, type_arg: ProperType
    ) -> Instance | TypeType | UnionType | AnyType | None:
        is_type, concrete = self._analyze_first_type_arg(type_arg)
        if concrete is None:
            return None

        querysets = tuple(self.realise_querysets(UnionType(concrete), self.lookup_info))
        return self._make_union(is_type, querysets)


make_resolver = AnnotationResolver.create
