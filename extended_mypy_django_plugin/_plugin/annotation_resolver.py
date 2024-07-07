import functools
from collections.abc import Iterator, Sequence
from typing import TYPE_CHECKING, cast

from mypy.nodes import Context, PlaceholderNode, TypeAlias, TypeInfo
from mypy.plugin import (
    AnalyzeTypeContext,
    AttributeContext,
    DynamicClassDefContext,
    FunctionContext,
    MethodContext,
)
from mypy.semanal import SemanticAnalyzer
from mypy.typeanal import TypeAnalyser
from mypy.types import (
    AnyType,
    Instance,
    PlaceholderType,
    ProperType,
    TypeOfAny,
    TypeType,
    UnionType,
    get_proper_type,
)
from mypy.types import Type as MypyType
from typing_extensions import Self, assert_never

from . import protocols


class ShouldDefer(Exception):
    pass


class FailedLookup(Exception):
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
        """
        This classmethod constructor lets us normalise the ctx to satisfy the interface the
        AnnotationResolver expects.

        Because each ctx type has a different api on it that provides a different set of
        abilities.
        """

        def sem_defer(sem_api: SemanticAnalyzer) -> bool:
            """
            The semantic analyzer is the only api that can actually defer

            Return True if was able to defer
            """
            if sem_api.final_iteration:
                return False
            else:
                sem_api.defer()
                return True

        def _lookup_info(sem_api: SemanticAnalyzer | None, fullname: str) -> TypeInfo | None:
            """
            If we have the semantic api, there's more we can do when trying to lookup
            some name
            """
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
            """
            When we have a TypeChecker we need to replicate close to what the semantic api
            does for named_type_or_none
            """
            sym = plugin_lookup_fully_qualified(fullname)
            if not sym or not isinstance(node := sym.node, TypeInfo):
                return None
            if args:
                return Instance(node, args)
            return Instance(node, [AnyType(TypeOfAny.special_form)] * len(node.defn.type_vars))

        def _lookup_alias(line: int, alias: str) -> Iterator[Instance | PlaceholderType]:
            """
            This is the same regardless of which ctx we have
            """
            try:
                sym = plugin_lookup_fully_qualified(alias)
            except AssertionError:
                raise FailedLookup(f"Failed to lookup {alias}")

            if not sym or isinstance(sym.node, PlaceholderNode):
                yield PlaceholderType(alias, [], line)
                return

            assert sym and isinstance(sym.node, TypeAlias)
            target = get_proper_type(sym.node.target)

            if isinstance(target, Instance):
                yield target
            elif isinstance(target, UnionType):
                for item in target.items:
                    found = get_proper_type(item)
                    assert isinstance(found, Instance | PlaceholderType)
                    yield found
            else:
                raise FailedLookup(f"Expected only an instance or union for {alias}: got {target}")

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
                lookup_alias = functools.partial(_lookup_alias, context.line)
                named_type_or_none = sem_api.named_type_or_none
            case AnalyzeTypeContext(api=api):
                assert isinstance(api, TypeAnalyser)
                assert isinstance(api.api, SemanticAnalyzer)
                context = ctx.context
                sem_api = api.api
                defer = functools.partial(sem_defer, sem_api)
                fail = functools.partial(sem_api.fail, ctx=context)
                lookup_info = functools.partial(_lookup_info, sem_api)
                lookup_alias = functools.partial(_lookup_alias, context.line)
                named_type_or_none = sem_api.named_type_or_none
            case AttributeContext(api=api) | MethodContext(api=api) | FunctionContext(api=api):
                context = ctx.context
                defer = lambda: False
                # The interface for the type checker says fail takes ctx
                # But the implementation of TypeChecker has it as context
                fail = functools.partial(api.fail, context=context)
                lookup_info = functools.partial(_lookup_info, None)
                lookup_alias = functools.partial(_lookup_alias, context.line)
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
        """
        Recursively flatten a union
        """
        if isinstance(typ, UnionType):
            for item in typ.items:
                yield from self._flatten_union(get_proper_type(item))
        else:
            yield typ

    def _concrete_for(
        self, model_type: ProperType, get_aliases: protocols.AliasGetter
    ) -> Instance | TypeType | UnionType | PlaceholderType | None:
        """
        Given some type that represents a model, and an alias getter, determine an
        Instance if we can from the model_type and use it with the alias getter.
        """
        is_type: bool = False

        found: ProperType = model_type
        if isinstance(model_type, TypeType):
            is_type = True
            found = model_type.item

        if isinstance(found, AnyType):
            did_defer = self._defer()
            if not did_defer:
                self.fail("Tried to use concrete annotations on a typing.Any")
            return None

        if not isinstance(found, Instance | UnionType):
            return None

        all_types = list(self._flatten_union(found))
        are_all_instances: bool = True
        names: list[str] = []
        concrete: list[Instance | PlaceholderType] = []

        for item in all_types:
            if not isinstance(item, Instance):
                self.fail(
                    f"Expected to operate on specific classes, got a {item.__class__.__name__}: {item}"
                )
                are_all_instances = False
                continue

            name = item.type.fullname
            names.append(name)
            concrete.extend(self._instances_from_aliases(get_aliases, name))

        if not are_all_instances:
            return None

        if not concrete:
            # We found instances, but couldn't get aliases
            # Either defer and we'll try again later or fail if we can't defer
            did_defer = self._defer()
            if not did_defer:
                self.fail(f"No concrete models found for {names}")
            return None

        return self._make_union(is_type, tuple(concrete))

    def _make_union(
        self, is_type: bool, instances: Sequence[Instance | PlaceholderType]
    ) -> UnionType | Instance | TypeType | PlaceholderType:
        """
        Given a sequence of instances, make them all TypeType if is_type and then
        return either the one type if the list is of 1, or the list wrapped in a UnionType
        """
        items: Sequence[UnionType | TypeType | Instance | PlaceholderType]

        if is_type:
            items = [TypeType(item) for item in instances]
        else:
            items = instances

        if len(items) == 1:
            return items[0]
        else:
            return UnionType(tuple(items))

    def _instances_from_aliases(
        self, get_aliases: protocols.AliasGetter, *models: str
    ) -> Iterator[Instance | PlaceholderType]:
        for model, alias in get_aliases(*models).items():
            if alias is None:
                self.fail(f"Failed to find concrete alias instance for '{model}'")
                continue

            try:
                yield from self.lookup_alias(alias)
            except FailedLookup as error:
                self.fail(
                    f"Failed to create concrete alias instance for '{model}' ({error}) (this is likely a bug in extended_mypy_django_plugin)"
                )

    def resolve(
        self, annotation: protocols.KnownAnnotations, model_type: ProperType
    ) -> Instance | TypeType | UnionType | PlaceholderType | None:
        if annotation is protocols.KnownAnnotations.CONCRETE:
            return self._concrete_for(model_type, self.get_concrete_aliases)

        elif annotation is protocols.KnownAnnotations.DEFAULT_QUERYSET:
            return self._concrete_for(model_type, self.get_queryset_aliases)

        else:
            assert_never(annotation)


make_resolver = AnnotationResolver.create

if TYPE_CHECKING:
    _R: protocols.Resolver = cast(AnnotationResolver, None)
