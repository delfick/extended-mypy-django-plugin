from typing import Final

from mypy.nodes import CallExpr, MemberExpr, MypyFile, SymbolNode, TypeInfo
from mypy.plugin import (
    AttributeContext,
    FunctionContext,
    MethodContext,
)
from mypy.types import (
    AnyType,
    CallableType,
    Instance,
    TypeOfAny,
    TypeQuery,
    TypeType,
    TypeVarType,
    UnionType,
    get_proper_type,
)
from mypy.types import Type as MypyType

from . import protocols, signature_info

TYPING_SELF: Final[str] = "typing.Self"
TYPING_EXTENSION_SELF: Final[str] = "typing_extensions.Self"


class HasAnnotations(TypeQuery[bool]):
    """
    Find where we have a concrete annotation
    """

    def __init__(self) -> None:
        super().__init__(any)

    def visit_callable_type(self, t: CallableType) -> bool:
        if t.type_guard:
            return t.type_guard.accept(self)
        else:
            return t.ret_type.accept(self)

    def visit_instance(self, t: Instance) -> bool:
        if super().visit_instance(t):
            return True
        return protocols.KnownAnnotations.resolve(t.type.fullname) is not None


class TypeChecking:
    def __init__(self, *, make_resolver: protocols.ResolverMaker) -> None:
        self.make_resolver = make_resolver

    def modify_return_type(self, ctx: MethodContext | FunctionContext) -> MypyType | None:
        info = signature_info.get_signature_info(ctx, self.make_resolver(ctx=ctx))
        if info is None:
            return None

        return info.resolve_return_type(ctx)

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


class ConcreteAnnotationChooser:
    """
    Helper for the plugin to tell Mypy to choose the plugin when we find functions/methods that
    return types using concrete annotations.

    At this point the only ones yet to be resolved should be using type vars.
    """

    def __init__(
        self,
        fullname: str,
        plugin_lookup_fully_qualified: protocols.LookupFullyQualified,
        is_function: bool,
        modules: dict[str, MypyFile] | None,
    ) -> None:
        self.fullname = fullname
        self._modules = modules
        self._is_function = is_function
        self._plugin_lookup_fully_qualified = plugin_lookup_fully_qualified

    def _get_symbolnode_for_fullname(self, fullname: str) -> SymbolNode | None:
        """
        Find the symbol representing the function or method we are analyzing.

        When analyzing a method we may find that the method is defined on a parent class
        and in that case we must assist mypy in finding where that is.
        """
        sym = self._plugin_lookup_fully_qualified(fullname)
        if sym and sym.node:
            return sym.node

        # Can't find the base class if we don't know the modules
        if self._modules is None:
            return None

        # If it's a function it should already have been found
        # We can only do more work if it's a method
        if self._is_function:
            return None

        if fullname.count(".") < 2:
            # Apparently it's possible for the hook to get something that is not what we expect
            return None

        # We're on a class and couldn't find the symbol, it's likely defined on a base class
        module, class_name, method_name = fullname.rsplit(".", 2)

        mod = self._modules.get(module)
        if mod is None:
            return None

        class_node = mod.names.get(class_name)
        if class_node is None:
            return None

        if not isinstance(class_node.node, TypeInfo):
            return None

        # Look at the base classes in mro order till we find the first mention of the method
        # that we are interested in
        for parent in class_node.node.mro:
            found = parent.names.get(method_name)
            if found:
                return found.node

        return None

    def choose(self) -> bool:
        """
        This is called for hooks that work on methods and functions.

        This means the node that we are operating is gonna be a FuncBas
        """
        sym_node = self._get_symbolnode_for_fullname(self.fullname)
        if not sym_node:
            return False

        if isinstance(sym_node, TypeInfo):
            # If the type is a class, then we are calling it's __call__ method
            if "__call__" not in sym_node.names:
                # If it doesn't have a __call__, then it's likely failing elsewhere
                return False

            sym_node = sym_node.names["__call__"].node

        # type will be the return type of the node
        # if it doesn't have type then it's likely an error somewhere else
        sym_node_type = getattr(sym_node, "type", None)
        if not isinstance(sym_node_type, MypyType):
            return False

        # Return if our type includes any kind of concrete annotation
        return sym_node_type.accept(HasAnnotations())
