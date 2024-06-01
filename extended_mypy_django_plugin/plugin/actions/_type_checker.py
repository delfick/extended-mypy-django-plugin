import dataclasses
from collections.abc import Iterator, Mapping
from typing import Protocol

from mypy.checker import TypeChecker
from mypy.nodes import (
    CallExpr,
    Context,
    Decorator,
    MemberExpr,
    MypyFile,
    OverloadedFuncDef,
    SymbolNode,
    SymbolTable,
    SymbolTableNode,
    TypeInfo,
    TypeVarExpr,
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


def _ret_from_node(node: SymbolNode | SymbolTableNode) -> ProperType | None:
    call = getattr(node, "type", None)

    while not isinstance(call, CallableType):
        if isinstance(call, Decorator):
            call = call.func
        elif isinstance(call, OverloadedFuncDef):
            call = call.items[-1]
        else:
            return None

    ret_type = call.ret_type
    if call.type_guard:
        ret_type = call.type_guard

    return get_proper_type(ret_type)


@dataclasses.dataclass
class DefiningScope:
    _api: TypeChecker
    _scopes: list[SymbolTable]

    def resolve(self, want: str) -> SymbolTableNode | None:
        if "." not in want:
            for scope in self._scopes:
                if want in scope:
                    return scope[want]
            return None
        else:
            first, rest = want.split(".", 1)
            for scope in self._scopes:
                if first in scope:
                    found = scope[first]
                    if not isinstance(found.node, MypyFile):
                        continue

                    return self.resolve(rest)
            return None

    def find_type_vars(
        self, item: MypyType, _chain: list[ProperType] | None = None
    ) -> tuple[list[tuple[bool, TypeVarType | str]], ProperType]:
        if _chain is None:
            _chain = []

        result: list[tuple[bool, TypeVarType | str]] = []

        item = get_proper_type(item)

        is_type: bool = False
        if isinstance(item, TypeType):
            is_type = True
            item = item.item

        if isinstance(item, UnboundType):
            node = self.resolve(item.name)
            if node and isinstance(node.node, TypeVarExpr):
                if node.node.fullname not in ("typing_extensions.Self", "typing.Self"):
                    result.append((is_type, node.node.name))

        if isinstance(item, TypeVarType):
            if item not in _chain:
                if item.fullname not in ("typing_extensions.Self", "typing.Self"):
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

        if isinstance(item, UnboundType):
            node = self.resolve(item.name)
            if node and isinstance(node.node, TypeInfo):
                item = Instance(node.node, [])

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
    type_vars: list[tuple[bool, TypeVarType | str]]
    lookup_info: _store.LookupInfo
    defining_scope: DefiningScope
    concrete_annotation: _known_annotations.KnownAnnotations | None

    @classmethod
    def create(
        cls,
        func: CallableType,
        fail: FailFunc,
        defining_scope: DefiningScope,
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

        concrete_annotation = defining_scope.determine_if_concrete(item)
        if concrete_annotation and not item_passed_in and isinstance(item, Instance | UnboundType):
            type_vars, item = defining_scope.find_type_vars(UnionType(item.args))
        else:
            type_vars, item = defining_scope.find_type_vars(item)

        if isinstance(item, UnionType) and len(item.items) == 1:
            item = item.items[0]

        return cls(
            func=func,
            fail=fail,
            item=get_proper_type(item),
            is_type=is_type,
            is_guard=is_guard,
            type_vars=type_vars,
            lookup_info=lookup_info,
            defining_scope=defining_scope,
            concrete_annotation=concrete_annotation,
        )

    def _clone_with_item(self, item: MypyType) -> Self:
        return self.create(
            func=self.func,
            fail=self.fail,
            item=item,
            lookup_info=self.lookup_info,
            defining_scope=self.defining_scope,
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

    def map_type_vars(
        self, ctx: MethodContext | FunctionContext
    ) -> Mapping[TypeVarType | str, Instance | TypeType]:
        result: dict[TypeVarType | str, Instance | TypeType] = {}

        formal_by_name = {arg.name: arg.typ for arg in self.func.formal_arguments()}

        for arg_name, arg_type in zip(ctx.callee_arg_names, ctx.arg_types):
            underlying = get_proper_type(formal_by_name[arg_name])
            if isinstance(underlying, TypeType):
                underlying = underlying.item

            if isinstance(underlying, TypeVarType):
                found_type = get_proper_type(arg_type[0])
                if isinstance(found_type, CallableType):
                    found_type = get_proper_type(found_type.ret_type)

                if isinstance(found_type, Instance):
                    result[underlying] = found_type
                    result[underlying.name] = found_type

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
                for self_name in ("typing_extension.Self", "typing.Self", "Self"):
                    result[self_name] = ctx_type

        for is_type, type_var in self.type_vars:
            if type_var not in result:
                self.fail(f"Failed to find an argument that matched the type var {type_var}")
            else:
                if is_type:
                    result[type_var] = TypeType(result[type_var])

        return result

    def transform(
        self,
        type_checking: "TypeChecking",
        context: Context,
        type_vars_map: Mapping[TypeVarType | str, Instance | TypeType],
        resolver: _annotation_resolver.AnnotationResolver,
    ) -> Instance | TypeType | UnionType | AnyType | None:
        if self.concrete_annotation is None:
            found: Instance | TypeType

            look: MypyType | str
            if isinstance(self.item, UnboundType):
                look = self.item.name
            else:
                look = self.item

            if isinstance(look, TypeVarType | str):
                if look in type_vars_map:
                    found = type_vars_map[look]
                else:
                    self.fail(f"Failed to work out type for type var {look}")
                    return AnyType(TypeOfAny.from_error)
            elif not isinstance(look, TypeType | Instance):
                self.fail(f"Got an unexpected item in the concrete annotation, {self.item}")
                return AnyType(TypeOfAny.from_error)
            else:
                found = look

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

    def _get_info(self, context: Context, is_function: bool) -> BasicTypeInfo | None:
        if not isinstance(context, CallExpr):
            return None

        if hasattr(self.api, "get_expression_type"):
            # In later mypy versions
            func = self.api.get_expression_type(context.callee)
        else:
            func = self.api.expr_checker.accept(context.callee)

        func = get_proper_type(func)

        if not isinstance(func, CallableType):
            return None

        if not func.definition:
            return None

        defining_scopes: list[SymbolTable] = []
        if is_function:
            module, _ = func.definition.fullname.rsplit(".", 1)
            class_name = ""
        else:
            module, class_name, _ = func.definition.fullname.rsplit(".", 2)

        if module not in self.api.modules:
            self.api.fail(f"Failed to find defining module: {module}", context)
            return None

        mod = self.api.modules[module]
        defining_scopes = [mod.names]
        if class_name:
            cls = mod.names[class_name]
            if not isinstance(cls.node, TypeInfo):
                self.api.fail(f"Failed to find defining class: {module}.{class_name}", context)
                return None
            defining_scopes.append(cls.node.names)

        return BasicTypeInfo.create(
            func=func,
            fail=lambda msg: self.api.fail(msg, context),
            lookup_info=self.lookup_info,
            defining_scope=DefiningScope(_api=self.api, _scopes=defining_scopes),
        )

    def check_typeguard(self, context: Context, is_function: bool) -> MypyType | None:
        info = self._get_info(context, is_function=is_function)
        if info is None:
            return None

        if info.is_guard and info.type_vars and info.contains_concrete_annotation:
            # Mypy plugin system doesn't currently provide an opportunity to resolve a type guard when it's for a concrete annotation that uses a type var
            self.api.fail(
                "Can't use a TypeGuard that uses a Concrete Annotation that uses type variables",
                context,
            )
            return AnyType(TypeOfAny.from_error)

        return None

    def modify_return_type(self, ctx: MethodContext | FunctionContext) -> MypyType | None:
        info = self._get_info(ctx.context, is_function=isinstance(ctx, FunctionContext))
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


class SharedAnnotationHookLogic:
    """
    Shared logic for modifying the return type of methods and functions that use a concrete
    annotation with a type variable.

    Note that the signature hook will already raise errors if a concrete annotation is
    used with a type var in a type guard.
    """

    def __init__(
        self,
        store: _store.Store,
        fullname: str,
        get_symbolnode_for_fullname: GetSymbolNode,
    ) -> None:
        self.store = store
        self.fullname = fullname
        self.get_symbolnode_for_fullname = get_symbolnode_for_fullname

    def choose(self) -> bool:
        """
        Choose methods and functions either returning a type guard or have a generic
        return type.

        We determine whether the return type is a concrete annotation or not in the run method.
        """
        if self.fullname.startswith("builtins."):
            return False

        sym_node = self.get_symbolnode_for_fullname(self.fullname)
        if not sym_node:
            return False

        ret_type = _ret_from_node(sym_node)
        if ret_type is None:
            return False

        if isinstance(ret_type, TypeType):
            ret_type = ret_type.item

        if isinstance(ret_type, UnboundType):
            return ret_type.name in [
                known.value.rpartition(".")[-1] for known in _known_annotations.KnownAnnotations
            ]
        elif isinstance(ret_type, Instance):
            try:
                _known_annotations.KnownAnnotations(ret_type.type.fullname)
            except ValueError:
                return False
            else:
                return True
        else:
            return False

    def run(self, ctx: MethodContext | FunctionContext) -> MypyType | None:
        assert isinstance(ctx.api, TypeChecker)

        type_checking = TypeChecking(self.store, api=ctx.api)

        return type_checking.modify_return_type(ctx)


class SharedSignatureHookLogic:
    """
    Shared logic for modifying the signature of methods and functions.

    This is only used to find cases where a concrete annotation with a type var
    is used in a type guard.

    In this situation the mypy plugin system does not provide an opportunity to fully resolve
    the type guard.
    """

    def __init__(
        self, store: _store.Store, fullname: str, get_symbolnode_for_fullname: GetSymbolNode
    ) -> None:
        self.store = store
        self.fullname = fullname
        self.get_symbolnode_for_fullname = get_symbolnode_for_fullname

    def choose(self) -> bool:
        """
        Only choose methods and functions that are returning a type guard
        """
        if self.fullname.startswith("builtins."):
            return False

        sym_node = self.get_symbolnode_for_fullname(self.fullname)
        if sym_node is None:
            return False

        ret_type = _ret_from_node(sym_node)
        if ret_type is None:
            return False

        if isinstance(ret_type, TypeType):
            ret_type = ret_type.item

        if not isinstance(ret_type, UnboundType):
            return False

        return ret_type.name in [
            known.value.rpartition(".")[-1] for known in _known_annotations.KnownAnnotations
        ]

    def run(self, ctx: MethodSigContext | FunctionSigContext) -> MypyType | None:
        assert isinstance(ctx.api, TypeChecker)

        type_checking = TypeChecking(self.store, api=ctx.api)

        return type_checking.check_typeguard(
            ctx.context, is_function=isinstance(ctx, FunctionSigContext)
        )
