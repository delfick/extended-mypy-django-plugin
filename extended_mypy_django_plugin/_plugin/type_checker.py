from mypy.nodes import CallExpr, Decorator, MemberExpr, MypyFile, SymbolNode, TypeInfo
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
    Overloaded,
    ProperType,
    TypeOfAny,
    TypeType,
    UnboundType,
    UnionType,
    get_proper_type,
)
from mypy.types import Type as MypyType

from . import protocols, signature_info


class TypeChecking:
    def __init__(self, *, make_resolver: protocols.ResolverMaker) -> None:
        self.make_resolver = make_resolver

    def check_typeguard(self, ctx: MethodSigContext | FunctionSigContext) -> FunctionLike | None:
        info = signature_info.get_signature_info(ctx, self.make_resolver(ctx=ctx))
        if info is None:
            return None

        if info.is_guard and info.returns_concrete_annotation_with_type_var:
            # Mypy plugin system doesn't currently provide an opportunity to resolve a type guard when it's for a concrete annotation that uses a type var
            ctx.api.fail(
                "Can't use a TypeGuard that uses a Concrete Annotation that uses type variables",
                ctx.context,
            )

            if info.unwrapped_type_guard:
                return ctx.default_signature.copy_modified(type_guard=info.unwrapped_type_guard)

        return None

    def modify_return_type(self, ctx: MethodContext | FunctionContext) -> MypyType | None:
        info = signature_info.get_signature_info(ctx, self.make_resolver(ctx=ctx))
        if info is None:
            return None

        return info.resolve_return_type(ctx)

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

    def _returns_annotation(self, typ: ProperType) -> bool:
        """
        Given a type, work out if it represents an annotated type.
        """
        if isinstance(typ, Overloaded):
            # Check if any of the overloaded signatures returns an annotation
            return any(self._returns_annotation(item) for item in typ.items)

        if isinstance(typ, Decorator):
            # Get the return type of the decorated function
            typ = typ.type

        if isinstance(typ, CallableType):
            # If we have a type guard, then ret_type will be a bool
            # but we wanna check what the type guard is for
            if typ.type_guard:
                typ = get_proper_type(typ.type_guard)
            else:
                typ = get_proper_type(typ.ret_type)

        # Unwrap a type[...]
        if isinstance(typ, TypeType):
            typ = typ.item

        # Unwrap if it's been wrapped by a previous hook
        if isinstance(typ, UnboundType) and typ.name == "__ConcreteWithTypeVar__":
            typ = get_proper_type(typ.args[0])

        # Make sure our wrapped type wasn't itself wrapped with type[...]
        if isinstance(typ, TypeType):
            typ = typ.item

        if not isinstance(typ, Instance):
            # Can't be an annotation if we don't have an Instance
            return False

        return protocols.KnownAnnotations.resolve(typ.type.fullname) is not None

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

        # We only choose functions/methods that return an annotation
        return self._returns_annotation(get_proper_type(sym_node_type))
