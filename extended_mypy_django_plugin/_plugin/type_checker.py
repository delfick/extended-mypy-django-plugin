from mypy.plugin import (
    FunctionContext,
    MethodContext,
)
from mypy.types import (
    AnyType,
    Instance,
    TypeOfAny,
    TypeType,
    TypeVarType,
    UnionType,
    get_proper_type,
)
from mypy.types import Type as MypyType

from . import protocols


class TypeChecking:
    def __init__(self, *, make_resolver: protocols.ResolverMaker) -> None:
        self.make_resolver = make_resolver

    def modify_cast_as_concrete(self, ctx: FunctionContext | MethodContext) -> MypyType:
        if len(ctx.arg_types) != 1:
            ctx.api.fail("Concrete.cast_as_concrete takes only one argument", ctx.context)
            return AnyType(TypeOfAny.from_error)

        if not ctx.arg_types[0]:
            ctx.api.fail("Mypy failed to tell us the type of the first argument", ctx.context)
            return AnyType(TypeOfAny.from_error)

        first_arg = get_proper_type(ctx.arg_types[0][0])
        if isinstance(first_arg, AnyType):
            ctx.api.fail("Failed to determine the type of the first argument", ctx.context)
            return AnyType(TypeOfAny.from_error)

        is_type: bool = False
        if isinstance(first_arg, TypeType):
            is_type = True
            first_arg = first_arg.item

        instances: list[Instance] = []
        if isinstance(first_arg, TypeVarType):
            if first_arg.values:
                for found in first_arg.values:
                    item = get_proper_type(found)
                    if isinstance(item, Instance):
                        instances.append(item)
                    else:
                        ctx.api.fail(
                            f"A value in the type var ({first_arg}) is unexpected: {item}: {type(item)}",
                            ctx.context,
                        )
                        return AnyType(TypeOfAny.from_error)
            else:
                item = get_proper_type(first_arg.upper_bound)
                if not isinstance(item, Instance):
                    ctx.api.fail(
                        f"Upper bound for type var ({first_arg}) is unexpected: {item}: {type(item)}",
                        ctx.context,
                    )
                    return AnyType(TypeOfAny.from_error)
                instances.append(item)

        elif isinstance(first_arg, Instance):
            instances.append(first_arg)

        elif isinstance(first_arg, UnionType):
            union_items = [get_proper_type(item) for item in first_arg.items]
            union_pairs = [
                (isinstance(part, TypeType), isinstance(part, Instance), part)
                for part in union_items
            ]
            are_all_instances = all(
                is_type or is_instance for is_type, is_instance, _ in union_pairs
            )
            if are_all_instances:
                for part in union_items:
                    found = part
                    if isinstance(found, TypeType):
                        is_type = True
                        found = found.item
                    if not isinstance(part, Instance):
                        are_all_instances = False
                        break
                    instances.append(part)

            if not are_all_instances:
                ctx.api.fail(
                    f"Expected only `type[MyClass]` or `MyClass` in a union provided to cast_as_concrete, got {union_items}",
                    ctx.context,
                )
                return AnyType(TypeOfAny.from_error)
        else:
            ctx.api.fail(
                f"cast_as_concrete must take a variable with a clear type, got {first_arg}: ({type(first_arg)})",
                ctx.context,
            )
            return AnyType(TypeOfAny.from_error)

        resolver = self.make_resolver(ctx=ctx)
        resolved = resolver.resolve(
            protocols.KnownAnnotations.CONCRETE, UnionType(tuple(instances))
        )
        if not resolved:
            # Error would have already been sent out
            return AnyType(TypeOfAny.from_error)

        if isinstance(resolved, UnionType):
            if is_type:
                resolved = UnionType(tuple(TypeType(item) for item in resolved.items))
        elif is_type:
            resolved = TypeType(resolved)

        return resolved
