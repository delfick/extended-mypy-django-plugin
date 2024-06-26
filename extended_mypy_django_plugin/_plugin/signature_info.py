import dataclasses
from collections.abc import Iterator, MutableMapping
from typing import Final

from mypy.checker import TypeChecker
from mypy.nodes import CallExpr, Context, Expression, IndexExpr
from mypy.plugin import FunctionContext, FunctionSigContext, MethodContext, MethodSigContext
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

from . import protocols

TYPING_SELF: Final[str] = "typing.Self"
TYPING_EXTENSION_SELF: Final[str] = "typing_extensions.Self"

_TypeVarMap = MutableMapping[TypeVarType | str, Instance | TypeType | UnionType]


@dataclasses.dataclass
class BasicTypeInfo:
    func: CallableType

    is_type: bool
    is_guard: bool

    item: ProperType
    type_vars: list[tuple[bool, TypeVarType]]
    resolver: protocols.Resolver
    concrete_annotation: protocols.KnownAnnotations | None
    unwrapped_type_guard: ProperType | None

    @classmethod
    def create(
        cls,
        func: CallableType,
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

        concrete_annotation: protocols.KnownAnnotations | None = None
        if isinstance(item, Instance):
            concrete_annotation = protocols.KnownAnnotations.resolve(item.type.fullname)

        if concrete_annotation and not item_passed_in and isinstance(item, Instance):
            type_vars, item = cls.find_type_vars(UnionType(item.args))
        else:
            type_vars, item = cls.find_type_vars(item)

        if isinstance(item, UnionType) and len(item.items) == 1:
            item = item.items[0]

        return cls(
            func=func,
            item=get_proper_type(item),
            is_type=is_type,
            is_guard=is_guard,
            type_vars=type_vars,
            resolver=resolver,
            concrete_annotation=concrete_annotation,
            unwrapped_type_guard=unwrapped_type_guard,
        )

    @classmethod
    def find_type_vars(
        cls, item: MypyType, _chain: list[ProperType] | None = None
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
                    for nxt_is_type, nxt in cls.find_type_vars(arg, _chain=_chain)[0]:
                        result.append((is_type or nxt_is_type, nxt))

        return result, item

    def _clone_with_item(self, item: MypyType) -> Self:
        return self.create(
            func=self.func,
            item=item,
            resolver=self.resolver,
        )

    @property
    def returns_concrete_annotation(self) -> bool:
        if self.concrete_annotation is not None:
            return True

        for item in self.items():
            if item.item is self.item:
                continue
            if item.returns_concrete_annotation:
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
            if arg_name not in formal_by_name:
                # arg isn't typed so can't be a type var!
                continue

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
        self, context: Context, type_vars_map: _TypeVarMap
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
            nxt = child.transform(context, type_vars_map)
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

    def resolve_return_type(self, ctx: MethodContext | FunctionContext) -> MypyType | None:
        type_vars_map = self.map_type_vars(ctx)

        result = self.transform(ctx.context, type_vars_map)
        if isinstance(result, UnionType) and len(result.items) == 1:
            return result.items[0]
        else:
            return result


def get_signature_info(
    ctx: MethodContext | FunctionContext | MethodSigContext | FunctionSigContext,
    resolver: protocols.Resolver,
) -> protocols.SignatureInfo | None:
    def get_expression_type(node: Expression, type_context: MypyType | None = None) -> MypyType:
        # We can remove the assert and switch to self.api.get_expression_type
        # when we don't have to support mypy 1.4
        assert isinstance(ctx.api, TypeChecker)
        return ctx.api.expr_checker.accept(node, type_context=type_context)

    found: ProperType | None = None

    if isinstance(ctx.context, CallExpr):
        found = get_proper_type(get_expression_type(ctx.context.callee))
    elif isinstance(ctx.context, IndexExpr):
        found = get_proper_type(get_expression_type(ctx.context.base))
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

    return BasicTypeInfo.create(func=func, resolver=resolver)
