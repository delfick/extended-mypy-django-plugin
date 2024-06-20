import abc
import dataclasses
from collections.abc import Callable, Iterator, MutableMapping
from typing import Final

from mypy.checker import TypeChecker
from mypy.nodes import (
    SYMBOL_FUNCBASE_TYPES,
    CallExpr,
    Context,
    Decorator,
    Expression,
    IndexExpr,
    MemberExpr,
    MypyFile,
    RefExpr,
    SymbolNode,
    SymbolTableNode,
    TypeInfo,
    Var,
)
from mypy.plugin import (
    AttributeContext,
    CheckerPluginInterface,
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

from . import protocols

TYPING_SELF: Final[str] = "typing.Self"
TYPING_EXTENSION_SELF: Final[str] = "typing_extensions.Self"

_TypeVarMap = MutableMapping[TypeVarType | str, Instance | TypeType | UnionType]


@dataclasses.dataclass
class Finder:
    _api: CheckerPluginInterface

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

    def determine_if_concrete(self, item: ProperType) -> protocols.KnownAnnotations | None:
        concrete_annotation: protocols.KnownAnnotations | None = None

        if isinstance(item, Instance):
            try:
                concrete_annotation = protocols.KnownAnnotations(item.type.fullname)
            except ValueError:
                pass

        return concrete_annotation


@dataclasses.dataclass
class BasicTypeInfo:
    func: CallableType

    is_type: bool
    is_guard: bool

    item: ProperType
    finder: Finder
    type_vars: list[tuple[bool, TypeVarType]]
    resolver: protocols.Resolver
    concrete_annotation: protocols.KnownAnnotations | None
    unwrapped_type_guard: ProperType | None

    @classmethod
    def create(
        cls,
        func: CallableType,
        finder: Finder,
        resolver: protocols.Resolver,
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
            item=get_proper_type(item),
            finder=finder,
            is_type=is_type,
            is_guard=is_guard,
            type_vars=type_vars,
            resolver=resolver,
            concrete_annotation=concrete_annotation,
            unwrapped_type_guard=unwrapped_type_guard,
        )

    def _clone_with_item(self, item: MypyType) -> Self:
        return self.create(
            func=self.func,
            item=item,
            finder=self.finder,
            resolver=self.resolver,
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
                    self.resolver.fail(
                        f"Failed to find an argument that matched the type var {type_var}"
                    )

            if found is not None:
                if is_type:
                    result[type_var] = TypeType(found)

        return result

    def transform(
        self,
        type_checking: "TypeChecking",
        context: Context,
        type_vars_map: _TypeVarMap,
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
                    self.resolver.fail(f"Failed to work out type for type var {self.item}")
                    return AnyType(TypeOfAny.from_error)
            elif not isinstance(self.item, TypeType | Instance):
                self.resolver.fail(
                    f"Got an unexpected item in the concrete annotation, {self.item}"
                )
                return AnyType(TypeOfAny.from_error)
            else:
                found = self.item

            if self.is_type and not isinstance(found, TypeType):
                return TypeType(found)
            else:
                return found

        models: list[Instance | TypeType] = []
        for child in self.items():
            nxt = child.transform(type_checking, context, type_vars_map)
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

        return self.resolver.resolve(self.concrete_annotation, arg)


class TypeChecking:
    def __init__(self, *, resolver: protocols.Resolver, api: CheckerPluginInterface) -> None:
        self.api = api
        self.resolver = resolver

    def get_expression_type(
        self, node: Expression, type_context: MypyType | None = None
    ) -> MypyType:
        # We can remove the assert and switch to self.api.get_expression_type
        # when we don't have to support mypy 1.4
        assert isinstance(self.api, TypeChecker)
        self.expr_checker = self.api.expr_checker
        return self.expr_checker.accept(node, type_context=type_context)

    def _get_info(self, context: Context) -> BasicTypeInfo | None:
        found: ProperType | None = None

        if isinstance(context, CallExpr):
            found = get_proper_type(self.get_expression_type(context.callee))
        elif isinstance(context, IndexExpr):
            found = get_proper_type(self.get_expression_type(context.base))
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
            finder=Finder(_api=self.api),
            resolver=self.resolver,
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

        result = info.transform(self, ctx.context, type_vars_map)
        if isinstance(result, UnionType) and len(result.items) == 1:
            return result.items[0]
        else:
            return result

    def extended_get_attribute_resolve_manager_method(
        self,
        ctx: AttributeContext,
        *,
        resolve_manager_method_from_instance: protocols.ResolveManagerMethodFromInstance,
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


class _SharedConcreteAnnotationLogic(abc.ABC):
    def __init__(
        self,
        make_resolver: Callable[
            [MethodContext | FunctionContext | MethodSigContext | FunctionSigContext],
            protocols.Resolver,
        ],
        fullname: str,
        plugin_lookup_fully_qualified: protocols.LookupFullyQualified,
        is_function: bool,
        modules: dict[str, MypyFile] | None,
    ) -> None:
        self.make_resolver = make_resolver
        self.fullname = fullname
        self._modules = modules
        self._is_function = is_function
        self._plugin_lookup_fully_qualified = plugin_lookup_fully_qualified

    def get_symbolnode_for_fullname(self, fullname: str) -> SymbolNode | SymbolTableNode | None:
        sym = self._plugin_lookup_fully_qualified(fullname)
        if sym and sym.node:
            return sym.node

        if self._is_function:
            return None

        if fullname.count(".") < 2:
            return None

        if self._modules is None:
            return None

        # We're on a class and couldn't find the sym, it's likely on a base class
        module, class_name, method_name = fullname.rsplit(".", 2)

        mod = self._modules.get(module)
        if mod is None:
            return None

        class_node = mod.names.get(class_name)
        if not class_node or not isinstance(class_node.node, TypeInfo):
            return None

        for parent in class_node.node.bases:
            if isinstance(parent.type, TypeInfo):
                if isinstance(found := parent.type.names.get(method_name), SymbolTableNode):
                    return found

        return None

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
                protocols.KnownAnnotations(ret_type.type.fullname)
            except ValueError:
                return False
            else:
                return True
        else:
            return False

    def _type_checking(
        self, ctx: MethodContext | FunctionContext | MethodSigContext | FunctionSigContext
    ) -> TypeChecking:
        return TypeChecking(resolver=self.make_resolver(ctx), api=ctx.api)


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
