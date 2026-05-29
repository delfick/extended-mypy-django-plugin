import importlib.metadata
from typing import Any

import mypy_django_plugin.django.context
import mypy_django_plugin.lib.helpers
import packaging.version
from mypy import checker_shared
from mypy.plugin import (
    FunctionContext,
    FunctionSigContext,
    MethodContext,
)
from mypy.types import (
    AnyType,
    FunctionLike,
    Instance,
    TypeAliasType,
    TypedDictType,
    TypeOfAny,
    TypeType,
    TypeVarType,
    UnionType,
    get_proper_type,
)
from mypy.types import Type as MypyType

from . import protocols


def _extract_model_type_from_queryset(queryset_type: Instance) -> Instance | None:
    args: list[Any] = [queryset_type]
    stubs_version = packaging.version.Version(importlib.metadata.version("django-stubs"))
    if stubs_version < packaging.version.Version("6.0.3"):
        # after django-stubs 6.0.3 the second argument was removed cause it is unused
        # A future version of extended-mypy-django-plugin will assume django-stubs>6.0.5
        args.append(None)

    return mypy_django_plugin.lib.helpers.extract_model_type_from_queryset(*args)


class TypeChecking:
    def __init__(self, *, make_resolver: protocols.ResolverMaker) -> None:
        self.make_resolver = make_resolver

    def modify_hide_queryset_annotations(
        self,
        *,
        ctx: FunctionSigContext,
        django_context: mypy_django_plugin.django.context.DjangoContext,
        scope: checker_shared.CheckerScope | None = None,
    ) -> FunctionLike:
        # First we need to make sure that what was pased in makes sense
        # We expect exactly one argument
        if len(ctx.args) != 1:
            ctx.api.fail("hide_queryset_annotations takes only one argument", ctx.context)
            return ctx.default_signature

        # We need mypy to tell us the type of this argument
        if not ctx.args[0]:
            ctx.api.fail("Mypy failed to tell us the type of the first argument", ctx.context)
            return ctx.default_signature

        # At this point it is an expression, but we are at the part of mypy where we can analyze it
        first_arg = get_proper_type(ctx.api.get_expression_type(ctx.args[0][0]))
        if isinstance(first_arg, AnyType):
            ctx.api.fail("Failed to determine the type of the first argument", ctx.context)
            return ctx.default_signature

        # If it's an alias then resolve what that's pointing to
        if isinstance(first_arg, TypeAliasType) and first_arg.alias:
            first_arg = get_proper_type(first_arg.alias.target)

        # We can't get the information we want if we're in a class method
        # So we only make sure we're passing in a queryset and otherwise ignore it
        if isinstance(first_arg, TypeVarType) and first_arg.name == "Self":
            if (
                scope is None
                or (enclosing := scope.enclosing_class()) is None
                or not enclosing.has_base("django.db.models.query.QuerySet")
            ):
                ctx.api.fail("First argument must be a queryset", ctx.context)

            return ctx.default_signature

        # We expect a queryset instance, it doesn't make sense to hide annotations on a type
        if not isinstance(first_arg, Instance):
            ctx.api.fail("First argument must be an instance", ctx.context)
            return ctx.default_signature

        # Now we get to something interesting!
        # We use django-stubs mypy plugin to extract the model type from our queryset
        # This function returns None if it's not a queryset or it couldn't find the model
        # We need the model because we want to make an annotation of the model without the annotations!
        model = _extract_model_type_from_queryset(first_arg)

        if model is None:
            ctx.api.fail(
                "Failed to determine a django model from the first argument (or it's not a queryset)",
                ctx.context,
            )
            return ctx.default_signature

        # Next we get that type of the model without annotations
        if not mypy_django_plugin.lib.helpers.is_annotated_model(model.type):
            django_model = Instance(model.type, [])
        else:
            django_model = Instance(model.type.bases[0].type, [])

        # Then we need to make sure we carry across the row type if it's a TypedDict
        # The second arg of a queryset will be a TypedDict if `.values` or `.values_list` has been used
        # And this type of queryset is very different than without that so we don't want to lose this information
        queryset_args: list[MypyType] = [django_model]
        if len(first_arg.args) == 2:
            second_arg = get_proper_type(first_arg.args[1])
            if isinstance(second_arg, TypeAliasType) and second_arg.alias:
                second_arg = get_proper_type(second_arg.alias.target)

            if (
                # If it's a TypedDict
                isinstance(second_arg, TypedDictType)
                # Or some kind of mapping because mypy couldn't find a more specific type
                or (
                    isinstance(second_arg, Instance) and second_arg.type.has_base("typing.Mapping")
                )
            ):
                # then we have a value queryset and we want to preserve that
                queryset_args.append(first_arg.args[1])

        # And finally we change the signature of our `hide_queryset_annotations` function at this callsite
        # Such that it takes in the type that we gave it
        # And returns an instance of the queryset we were given such that it's in terms
        # of the un-annotated model and any Values row type that we need to carry through
        return ctx.default_signature.copy_modified(
            arg_types=[first_arg], ret_type=Instance(first_arg.type, queryset_args)
        )

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
