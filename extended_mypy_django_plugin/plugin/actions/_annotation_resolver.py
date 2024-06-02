from collections.abc import Iterator, Sequence
from typing import Protocol

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
from typing_extensions import assert_never

from .. import _known_annotations, _store


class FailFunc(Protocol):
    def __call__(self, msg: str) -> None: ...


class DeferFunc(Protocol):
    def __call__(self) -> bool: ...


class TypeAnalyze(Protocol):
    def __call__(self, typ: MypyType, /) -> MypyType: ...


class NamedTypeOrNone(Protocol):
    def __call__(self, fullname: str, args: list[MypyType] | None = None) -> Instance | None: ...


class AnnotationResolver:
    def __init__(
        self,
        store: _store.Store,
        fail: FailFunc,
        defer: DeferFunc,
        lookup_info: _store.LookupInfo,
        named_type_or_none: NamedTypeOrNone,
    ) -> None:
        self._store = store
        self._fail = fail
        self._defer = defer
        self._named_type_or_none = named_type_or_none
        self._lookup_info = lookup_info

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
            self._fail("Tried to use concrete annotations on a typing.Any")
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
                self._fail(
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
                self._store.retrieve_concrete_children_types(
                    item.type, self._lookup_info, self._named_type_or_none
                )
            )

        if not concrete:
            if not self._defer():
                self._fail(f"No concrete models found for {names}")
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
            self._fail("Concrete annotations must contain exactly one argument")
            return None, False

        type_arg = get_proper_type(analyze_type(args[0]))
        needs_rewrap = self._has_typevars(type_arg)
        return type_arg, needs_rewrap

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

        try:
            querysets = tuple(
                self._store.realise_querysets(UnionType(concrete), self._lookup_info)
            )
        except _store.RestartDmypy as err:
            self._fail(f"You probably need to restart dmypy: {err}")
            return AnyType(TypeOfAny.from_error)
        except _store.UnionMustBeOfTypes:
            self._fail("Union must be of instances of models")
            return None
        else:
            return self._make_union(is_type, querysets)
