import dataclasses
from typing import TYPE_CHECKING, Final, cast

from mypy.checker import TypeChecker
from mypy.nodes import CallExpr, Expression, IndexExpr
from mypy.plugin import FunctionContext, MethodContext
from mypy.types import (
    CallableType,
    Instance,
    ProperType,
    TypeAliasType,
    TypeTranslator,
    TypeType,
    TypeVarType,
    UnionType,
    get_proper_type,
)
from mypy.types import Type as MypyType
from typing_extensions import Self

from . import protocols

TYPING_SELF: Final[str] = "typing.Self"
TYPING_EXTENSION_SELF: Final[str] = "typing_extensions.Self"


class ResolveAnnotations(TypeTranslator):
    """
    Use visitor pattern to recursively resolve concrete annotations
    """

    def __init__(
        self,
        ctx: MethodContext | FunctionContext,
        resolver: protocols.Resolver,
        type_vars_map: protocols.TypeVarMap,
    ) -> None:
        self.ctx = ctx
        self.resolver = resolver
        self.type_vars_map = type_vars_map

    def visit_instance(self, t: Instance) -> MypyType:
        item = get_proper_type(super().visit_instance(t))
        if not isinstance(item, Instance):
            return item

        t = item

        annotation = protocols.KnownAnnotations.resolve(t.type.fullname)
        if not annotation:
            return item

        if len(t.args) != 1:
            # Would be an error elsewhere
            return t

        inner = get_proper_type(t.args[0])

        resolved = self.resolver.resolve(annotation, inner)
        # Already put out an error if we couldn't resolve
        if resolved is None:
            return t

        return resolved

    def visit_type_var(self, t: TypeVarType) -> MypyType:
        if self.type_vars_map is None:
            return t

        if t in self.type_vars_map:
            return self.type_vars_map[t].accept(self)
        else:
            return t

    def visit_type_alias_type(self, t: TypeAliasType) -> MypyType:
        return t.copy_modified(args=[a.accept(self) for a in t.args])


@dataclasses.dataclass
class _SignatureTypeInfo:
    """
    Used to represent information about a method/function signature.

    This is so we can do type variable substitution and resolve a return type for a method/function
    """

    func: CallableType
    is_guard: bool
    transformed_ret_type: ProperType

    @classmethod
    def create(
        cls,
        *,
        ctx: MethodContext | FunctionContext,
        func: CallableType,
        resolver: protocols.Resolver,
    ) -> Self:
        is_guard: bool = False

        if func.type_guard:
            is_guard = True
            item = func.type_guard
        else:
            item = func.ret_type

        type_vars_map = cls._map_type_vars(func=func, ctx=ctx)
        transformer = ResolveAnnotations(ctx=ctx, resolver=resolver, type_vars_map=type_vars_map)
        ret_type = get_proper_type(item.accept(transformer))

        return cls(func=func, is_guard=is_guard, transformed_ret_type=ret_type)

    @classmethod
    def _map_type_vars(
        cls, *, func: CallableType, ctx: MethodContext | FunctionContext
    ) -> protocols.TypeVarMap:
        result: protocols.TypeVarMap = {}

        if isinstance(ctx, MethodContext | FunctionContext):
            formal_by_name = {arg.name: arg.typ for arg in func.formal_arguments()}

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
                if (
                    func.variables
                    and isinstance(func.variables[0], TypeVarType)
                    and func.variables[0].name == "Self"
                ):
                    result[func.variables[0]] = ctx_type

        return result


def get_signature_info(
    ctx: MethodContext | FunctionContext, resolver: protocols.Resolver
) -> protocols.SignatureInfo | None:
    def get_expression_type(node: Expression, type_context: MypyType | None = None) -> MypyType:
        # We can remove the assert and switch to self.api.get_expression_type
        # when we don't have to support mypy 1.4
        assert isinstance(ctx.api, TypeChecker)
        return ctx.api.expr_checker.accept(node, type_context=type_context)

    found: ProperType | None = None

    # normalise the difference between `func()` and `namespace.func()`
    if isinstance(ctx.context, CallExpr):
        found = get_proper_type(get_expression_type(ctx.context.callee))
    elif isinstance(ctx.context, IndexExpr):
        found = get_proper_type(get_expression_type(ctx.context.base))
        if isinstance(found, Instance) and found.args:
            found = get_proper_type(found.args[-1])

    if found is None:
        return None

    # If we found a class, then we want to use `instance.__call__` as the function to analyze
    if isinstance(found, Instance):
        if not (call := found.type.names.get("__call__")) or not (calltype := call.type):
            return None

        func = get_proper_type(calltype)
    else:
        func = found

    if not isinstance(func, CallableType):
        return None

    return _SignatureTypeInfo.create(ctx=ctx, func=func, resolver=resolver)


if TYPE_CHECKING:
    _SI: protocols.SignatureInfo = cast(_SignatureTypeInfo, None)
