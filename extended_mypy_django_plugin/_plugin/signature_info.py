import dataclasses
from collections.abc import Sequence
from typing import Final

from mypy.checker import TypeChecker
from mypy.nodes import CallExpr, Expression, IndexExpr
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


@dataclasses.dataclass
class _SignatureTypeInfo:
    """
    Used to represent information about a method/function signature.

    This is so we can do type variable substitution and resolve a return type for a method/function
    """

    func: CallableType

    is_type: bool
    is_guard: bool

    ret_types: Sequence[
        tuple[protocols.KnownAnnotations | None, ProperType, bool, TypeVarType | None]
    ]

    resolver: protocols.Resolver
    unwrapped_type_guard: ProperType | None

    @classmethod
    def create(cls, *, func: CallableType, resolver: protocols.Resolver) -> Self:
        is_type: bool = False
        is_guard: bool = False

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
            item = get_proper_type(item.args[0])
            unwrapped_type_guard = item
            if is_type:
                unwrapped_type_guard = TypeType(unwrapped_type_guard)

        if isinstance(item, TypeType):
            is_type = True
            item = item.item

        if isinstance(item, UnionType):
            found_ret_types = tuple(get_proper_type(i) for i in item.items)
        else:
            found_ret_types = (item,)

        ret_types: list[
            tuple[protocols.KnownAnnotations | None, ProperType, bool, TypeVarType | None]
        ] = []

        for found in found_ret_types:
            type_var: TypeVarType | None = None
            found_is_type: bool = False
            annotation: protocols.KnownAnnotations | None = None

            bare: ProperType = found
            if isinstance(found, TypeType):
                found_is_type = True
                bare = found.item

            if isinstance(bare, Instance):
                annotation = protocols.KnownAnnotations.resolve(bare.type.fullname)

                if annotation:
                    bare = get_proper_type(bare.args[0])

            if isinstance(bare, TypeVarType):
                type_var = bare

            ret_types.append((annotation, bare, found_is_type, type_var))

        return cls(
            func=func,
            is_type=is_type,
            is_guard=is_guard,
            resolver=resolver,
            ret_types=ret_types,
            unwrapped_type_guard=unwrapped_type_guard,
        )

    @property
    def returns_concrete_annotation_with_type_var(self) -> bool:
        return any(
            annotation is not None and type_var is not None
            for annotation, _, _, type_var in self.ret_types
        )

    def _map_type_vars(self, ctx: MethodContext | FunctionContext) -> protocols.TypeVarMap:
        result: protocols.TypeVarMap = {}

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

        for _, _, is_type, type_var in self.ret_types:
            if type_var is None:
                continue

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

    def resolve_return_type(self, ctx: MethodContext | FunctionContext) -> MypyType | None:
        if not self.returns_concrete_annotation_with_type_var:
            # Nothing to substitute!
            return None

        if self.is_guard:
            # Mypy plugin system doesn't currently provide an opportunity to resolve a type guard
            # when it's for a concrete annotation that uses a type var
            return None

        final: list[MypyType] = []
        type_vars_map = self._map_type_vars(ctx)

        for annotation, item, is_type, type_var in self.ret_types:
            replaced: MypyType
            if type_var is None and annotation is None:
                replaced = item
            else:
                if type_var is None:
                    replaced = item
                elif type_var in type_vars_map:
                    replaced = type_vars_map[type_var]
                elif type_var.fullname in [TYPING_EXTENSION_SELF, TYPING_SELF] or (
                    type_var.name == "Self" and TYPING_SELF in type_vars_map
                ):
                    replaced = type_vars_map[TYPING_SELF]
                else:
                    self.resolver.fail(f"Failed to work out type for type var {type_var}")
                    return AnyType(TypeOfAny.from_error)

            if annotation is not None:
                resolved = self.resolver.resolve(annotation, replaced)
                if resolved is None:
                    self.resolver.fail(
                        f"Got an unexpected item in the concrete annotation, {replaced}"
                    )
                    return AnyType(TypeOfAny.from_error)
                else:
                    replaced = resolved

            if is_type or self.is_type:
                final.append(TypeType(replaced))
            else:
                final.append(replaced)

        if len(final) == 1:
            return final[0]
        else:
            return UnionType(tuple(final))


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

    return _SignatureTypeInfo.create(func=func, resolver=resolver)
