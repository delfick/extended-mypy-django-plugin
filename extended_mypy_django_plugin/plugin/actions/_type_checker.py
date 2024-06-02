import abc
import dataclasses
from collections.abc import Iterator, MutableMapping
from typing import Final, Protocol

from mypy.checker import TypeChecker
from mypy.nodes import (
    SYMBOL_FUNCBASE_TYPES,
    CallExpr,
    Context,
    Decorator,
    IndexExpr,
    MemberExpr,
    RefExpr,
    SymbolNode,
    SymbolTableNode,
    TypeInfo,
    Var,
)
from mypy.plugin import (
    AttributeContext,
    FunctionContext,
    FunctionSigContext,
    MethodContext,
    MethodSigContext,
)
from mypy.types import (
    AnyType,
    CallableType,
    FunctionLike,
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
from typing_extensions import Self

from .. import _known_annotations, _store
from . import _annotation_resolver


class FailFunc(Protocol):
    def __call__(self, message: str) -> None: ...


class ResolveManagerMethodFromInstance(Protocol):
    def __call__(
        self, instance: Instance, method_name: str, ctx: AttributeContext
    ) -> MypyType: ...


class GetSymbolNode(Protocol):
    def __call__(self, fullname: str) -> SymbolNode | SymbolTableNode | None: ...


TYPING_SELF: Final[str] = "typing.Self"
TYPING_EXTENSION_SELF: Final[str] = "typing_extensions.Self"

_TypeVarMap = MutableMapping[TypeVarType | str, Instance | TypeType | UnionType]


@dataclasses.dataclass
class Finder:
    _api: TypeChecker

    def find_type_vars(
        self, item: MypyType, _chain: list[ProperType] | None = None
    ) -> tuple[list[tuple[bool, TypeVarType]], ProperType]:
        if _chain is None:
            _chain = []

        result: list[tuple[bool, TypeVarType]] = []

        item = get_proper_type(item)

        is_type: bool = False
        if isinstance(item, TypeType):
            is_type = True
            item = item.item

        if isinstance(item, TypeVarType):
            if item.fullname not in [TYPING_EXTENSION_SELF, TYPING_SELF]:
                result.append((is_type, item))

        elif isinstance(item, UnionType):
            for arg in item.items:
                proper = get_proper_type(arg)
                if isinstance(proper, TypeType):
                    proper = proper.item

                if proper not in _chain:
                    _chain.append(proper)
                    for nxt_is_type, nxt in self.find_type_vars(arg, _chain=_chain)[0]:
                        result.append((is_type or nxt_is_type, nxt))

        return result, item

    def determine_if_concrete(
        self, item: ProperType
    ) -> _known_annotations.KnownAnnotations | None:
        concrete_annotation: _known_annotations.KnownAnnotations | None = None

        if isinstance(item, Instance):
            try:
                concrete_annotation = _known_annotations.KnownAnnotations(item.type.fullname)
            except ValueError:
                pass

        return concrete_annotation


@dataclasses.dataclass
class BasicTypeInfo:
    func: CallableType
    fail: FailFunc

    is_type: bool
    is_guard: bool

    item: ProperType
    finder: Finder
    type_vars: list[tuple[bool, TypeVarType]]
    lookup_info: _store.LookupInfo
    concrete_annotation: _known_annotations.KnownAnnotations | None
    unwrapped_type_guard: ProperType | None

    @classmethod
    def create(
        cls,
        func: CallableType,
        fail: FailFunc,
        finder: Finder,
        lookup_info: _store.LookupInfo,
        item: MypyType | None = None,
    ) -> Self:
        is_type: bool = False
        is_guard: bool = False

        item_passed_in: bool = item is not None

        if item is None:
            if func.type_guard:
                is_guard = True
                item = func.type_guard
            else:
                item = func.ret_type

        item = get_proper_type(item)
        if isinstance(item, TypeType):
            is_type = True
            item = item.item

        unwrapped_type_guard: ProperType | None = None
        if isinstance(item, UnboundType) and item.name == "__ConcreteWithTypeVar__":
            unwrapped_type_guard = get_proper_type(item.args[0])
            if is_type:
                unwrapped_type_guard = TypeType(unwrapped_type_guard)

            item = item.args[0]

        item = get_proper_type(item)
        if isinstance(item, TypeType):
            is_type = True
            item = item.item

        concrete_annotation = finder.determine_if_concrete(item)
        if concrete_annotation and not item_passed_in and isinstance(item, Instance):
            type_vars, item = finder.find_type_vars(UnionType(item.args))
        else:
            type_vars, item = finder.find_type_vars(item)

        if isinstance(item, UnionType) and len(item.items) == 1:
            item = item.items[0]

        return cls(
            func=func,
            fail=fail,
            item=get_proper_type(item),
            finder=finder,
            is_type=is_type,
            is_guard=is_guard,
            type_vars=type_vars,
            lookup_info=lookup_info,
            concrete_annotation=concrete_annotation,
            unwrapped_type_guard=unwrapped_type_guard,
        )

    def _clone_with_item(self, item: MypyType) -> Self:
        return self.create(
            func=self.func,
            fail=self.fail,
            item=item,
            finder=self.finder,
            lookup_info=self.lookup_info,
        )

    @property
    def contains_concrete_annotation(self) -> bool:
        if self.concrete_annotation is not None:
            return True

        for item in self.items():
            if item.item is self.item:
                continue
            if item.contains_concrete_annotation:
                return True

        return False

    def items(self) -> Iterator[Self]:
        if isinstance(self.item, UnionType):
            for item in self.item.items:
                yield self._clone_with_item(item)
        else:
            yield self._clone_with_item(self.item)

    def map_type_vars(self, ctx: MethodContext | FunctionContext) -> _TypeVarMap:
        result: _TypeVarMap = {}

        formal_by_name = {arg.name: arg.typ for arg in self.func.formal_arguments()}

        for arg_name, arg_type in zip(ctx.callee_arg_names, ctx.arg_types):
            underlying = get_proper_type(formal_by_name[arg_name])
            if isinstance(underlying, TypeType):
                underlying = underlying.item

            if isinstance(underlying, TypeVarType):
                found_type = get_proper_type(arg_type[0])

                if isinstance(found_type, CallableType):
                    found_type = get_proper_type(found_type.ret_type)

                if isinstance(found_type, TypeType):
                    found_type = found_type.item

                if isinstance(found_type, UnionType):
                    found_type = UnionType(
                        tuple(
                            item
                            if not isinstance(item := get_proper_type(it), TypeType)
                            else item.item
                            for it in found_type.items
                        )
                    )

                if isinstance(found_type, Instance | UnionType):
                    result[underlying] = found_type

        if isinstance(ctx, MethodContext):
            ctx_type = ctx.type
            if isinstance(ctx_type, TypeType):
                ctx_type = ctx_type.item

            if isinstance(ctx.type, CallableType):
                if isinstance(ctx.type.ret_type, Instance | TypeType):
                    ctx_type = ctx.type.ret_type

            if isinstance(ctx_type, TypeType):
                ctx_type = ctx_type.item

            if isinstance(ctx_type, Instance):
                for self_name in [TYPING_EXTENSION_SELF, TYPING_SELF]:
                    result[self_name] = ctx_type

        for is_type, type_var in self.type_vars:
            found: ProperType | None = None
            if type_var in result:
                found = result[type_var]
            else:
                choices = [
                    v
                    for k, v in result.items()
                    if (isinstance(k, TypeVarType) and k.name == type_var.name)
                    or (k == TYPING_SELF and type_var.name == "Self")
                ]
                if len(choices) == 1:
                    result[type_var] = choices[0]
                else:
                    self.fail(f"Failed to find an argument that matched the type var {type_var}")

            if found is not None:
                if is_type:
                    result[type_var] = TypeType(found)

        return result

    def transform(
        self,
        type_checking: "TypeChecking",
        context: Context,
        type_vars_map: _TypeVarMap,
        resolver: _annotation_resolver.AnnotationResolver,
    ) -> Instance | TypeType | UnionType | AnyType | None:
        if self.concrete_annotation is None:
            found: Instance | TypeType | UnionType

            if isinstance(self.item, TypeVarType):
                if self.item in type_vars_map:
                    found = type_vars_map[self.item]
                elif self.item.fullname in [TYPING_EXTENSION_SELF, TYPING_SELF]:
                    found = type_vars_map[self.item.fullname]
                elif self.item.name == "Self" and TYPING_SELF in type_vars_map:
                    found = type_vars_map[TYPING_SELF]
                else:
                    self.fail(f"Failed to work out type for type var {self.item}")
                    return AnyType(TypeOfAny.from_error)
            elif not isinstance(self.item, TypeType | Instance):
                self.fail(f"Got an unexpected item in the concrete annotation, {self.item}")
                return AnyType(TypeOfAny.from_error)
            else:
                found = self.item

            if self.is_type and not isinstance(found, TypeType):
                return TypeType(found)
            else:
                return found

        models: list[Instance | TypeType] = []
        for child in self.items():
            nxt = child.transform(type_checking, context, type_vars_map, resolver=resolver)
            if nxt is None or isinstance(nxt, AnyType | UnionType):
                # Children in self.items() should never return UnionType from transform
                return nxt

            if self.is_type and not isinstance(nxt, TypeType):
                nxt = TypeType(nxt)

            models.append(nxt)

        arg: MypyType
        if len(models) == 1:
            arg = models[0]
        else:
            arg = UnionType(tuple(models))

        return resolver.resolve(self.concrete_annotation, arg)


class TypeChecking:
    def __init__(self, store: _store.Store, *, api: TypeChecker) -> None:
        self.api = api
        self.store = store

    def _named_type_or_none(
        self, fullname: str, args: list[MypyType] | None = None
    ) -> Instance | None:
        node = self.lookup_info(fullname)
        if not isinstance(node, TypeInfo):
            return None
        if args:
            return Instance(node, args)
        return Instance(node, [AnyType(TypeOfAny.special_form)] * len(node.defn.type_vars))

    def _named_type(self, fullname: str, args: list[MypyType] | None = None) -> Instance:
        node = self.lookup_info(fullname)
        assert isinstance(node, TypeInfo)
        if args:
            return Instance(node, args)
        return Instance(node, [AnyType(TypeOfAny.special_form)] * len(node.defn.type_vars))

    def _get_info(self, context: Context) -> BasicTypeInfo | None:
        found: ProperType | None = None
        if isinstance(context, CallExpr):
            found = get_proper_type(self.api.expr_checker.accept(context.callee))
        elif isinstance(context, IndexExpr):
            found = get_proper_type(self.api.expr_checker.accept(context.base))
            if isinstance(found, Instance) and found.args:
                found = get_proper_type(found.args[-1])

        if found is None:
            return None

        if isinstance(found, Instance):
            if not (call := found.type.names.get("__call__")) or not (calltype := call.type):
                return None

            func = get_proper_type(calltype)
        else:
            func = found

        if not isinstance(func, CallableType):
            return None

        return BasicTypeInfo.create(
            func=func,
            fail=lambda msg: self.api.fail(msg, context),
            finder=Finder(_api=self.api),
            lookup_info=self.lookup_info,
        )

    def check_typeguard(self, ctx: MethodSigContext | FunctionSigContext) -> FunctionLike | None:
        info = self._get_info(ctx.context)
        if info is None:
            return None

        if info.is_guard and info.type_vars and info.contains_concrete_annotation:
            # Mypy plugin system doesn't currently provide an opportunity to resolve a type guard when it's for a concrete annotation that uses a type var
            self.api.fail(
                "Can't use a TypeGuard that uses a Concrete Annotation that uses type variables",
                ctx.context,
            )

            if info.unwrapped_type_guard:
                return ctx.default_signature.copy_modified(type_guard=info.unwrapped_type_guard)

        return None

    def modify_return_type(self, ctx: MethodContext | FunctionContext) -> MypyType | None:
        info = self._get_info(ctx.context)
        if info is None:
            return None

        if info.is_guard and info.type_vars and info.concrete_annotation is not None:
            # Mypy plugin system doesn't currently provide an opportunity to resolve a type guard when it's for a concrete annotation that uses a type var
            return None

        if not info.contains_concrete_annotation:
            return None

        type_vars_map = info.map_type_vars(ctx)

        resolver = _annotation_resolver.AnnotationResolver(
            self.store,
            defer=lambda: True,
            fail=lambda msg: ctx.api.fail(msg, ctx.context),
            lookup_info=self.lookup_info,
            named_type_or_none=self._named_type_or_none,
        )

        result = info.transform(self, ctx.context, type_vars_map, resolver=resolver)
        if isinstance(result, UnionType) and len(result.items) == 1:
            return result.items[0]
        else:
            return result

    def extended_get_attribute_resolve_manager_method(
        self,
        ctx: AttributeContext,
        *,
        resolve_manager_method_from_instance: ResolveManagerMethodFromInstance,
    ) -> MypyType:
        """
        Copied from django-stubs after https://github.com/typeddjango/django-stubs/pull/2027

        A 'get_attribute_hook' that is intended to be invoked whenever the TypeChecker encounters
        an attribute on a class that has 'django.db.models.BaseManager' as a base.
        """
        # Skip (method) type that is currently something other than Any of type `implementation_artifact`
        default_attr_type = get_proper_type(ctx.default_attr_type)
        if not isinstance(default_attr_type, AnyType):
            return default_attr_type
        elif default_attr_type.type_of_any != TypeOfAny.implementation_artifact:
            return default_attr_type

        # (Current state is:) We wouldn't end up here when looking up a method from a custom _manager_.
        # That's why we only attempt to lookup the method for either a dynamically added or reverse manager.
        if isinstance(ctx.context, MemberExpr):
            method_name = ctx.context.name
        elif isinstance(ctx.context, CallExpr) and isinstance(ctx.context.callee, MemberExpr):
            method_name = ctx.context.callee.name
        else:
            ctx.api.fail("Unable to resolve return type of queryset/manager method", ctx.context)
            return AnyType(TypeOfAny.from_error)

        if isinstance(ctx.type, Instance):
            return resolve_manager_method_from_instance(
                instance=ctx.type, method_name=method_name, ctx=ctx
            )
        elif isinstance(ctx.type, UnionType) and all(
            isinstance(get_proper_type(instance), Instance) for instance in ctx.type.items
        ):
            items: list[Instance] = []
            for instance in ctx.type.items:
                inst = get_proper_type(instance)
                if isinstance(inst, Instance):
                    items.append(inst)

            resolved = tuple(
                resolve_manager_method_from_instance(
                    instance=inst, method_name=method_name, ctx=ctx
                )
                for inst in items
            )
            return UnionType(resolved)
        else:
            ctx.api.fail(
                f'Unable to resolve return type of queryset/manager method "{method_name}"',
                ctx.context,
            )
            return AnyType(TypeOfAny.from_error)

    def lookup_info(self, fullname: str) -> TypeInfo | None:
        return self.store.plugin_lookup_info(fullname)


class _SharedConcreteAnnotationLogic(abc.ABC):
    def __init__(
        self,
        store: _store.Store,
        fullname: str,
        get_symbolnode_for_fullname: GetSymbolNode,
    ) -> None:
        self.store = store
        self.fullname = fullname
        self.get_symbolnode_for_fullname = get_symbolnode_for_fullname

    def _choose_with_concrete_annotation(self) -> bool:
        sym_node = self.get_symbolnode_for_fullname(self.fullname)
        if not sym_node:
            return False

        if isinstance(sym_node, TypeInfo):
            if "__call__" not in sym_node.names:
                return False
            ret_type = sym_node.names["__call__"].type
        elif isinstance(
            sym_node, (*SYMBOL_FUNCBASE_TYPES, Decorator, SymbolTableNode, Var, RefExpr)
        ):
            ret_type = sym_node.type
        else:
            return False

        ret_type = get_proper_type(ret_type)

        if isinstance(ret_type, CallableType):
            if ret_type.type_guard:
                ret_type = get_proper_type(ret_type.type_guard)
            else:
                ret_type = get_proper_type(ret_type.ret_type)

        if isinstance(ret_type, TypeType):
            ret_type = ret_type.item

        if isinstance(ret_type, UnboundType) and ret_type.name == "__ConcreteWithTypeVar__":
            ret_type = get_proper_type(ret_type.args[0])

        if isinstance(ret_type, Instance):
            try:
                _known_annotations.KnownAnnotations(ret_type.type.fullname)
            except ValueError:
                return False
            else:
                return True
        else:
            return False

    def _type_checking(
        self, ctx: MethodContext | FunctionContext | MethodSigContext | FunctionSigContext
    ) -> TypeChecking:
        assert isinstance(ctx.api, TypeChecker)

        return TypeChecking(self.store, api=ctx.api)


class SharedModifyReturnTypeLogic(_SharedConcreteAnnotationLogic):
    """
    Shared logic for modifying the return type of methods and functions that use a concrete
    annotation with a type variable.

    Note that the signature hook will already raise errors if a concrete annotation is
    used with a type var in a type guard.
    """

    def choose(self) -> bool:
        return self._choose_with_concrete_annotation()

    def run(self, ctx: MethodContext | FunctionContext) -> MypyType | None:
        return self._type_checking(ctx).modify_return_type(ctx)


class SharedCheckTypeGuardsLogic(_SharedConcreteAnnotationLogic):
    """
    Shared logic for modifying the signature of methods and functions.

    This is only used to find cases where a concrete annotation with a type var
    is used in a type guard.

    In this situation the mypy plugin system does not provide an opportunity to fully resolve
    the type guard.
    """

    def choose(self) -> bool:
        return self._choose_with_concrete_annotation()

    def run(self, ctx: MethodSigContext | FunctionSigContext) -> FunctionLike | None:
        return self._type_checking(ctx).check_typeguard(ctx)
