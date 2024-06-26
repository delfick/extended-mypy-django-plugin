from mypy.nodes import (
    SYMBOL_FUNCBASE_TYPES,
    CallExpr,
    Decorator,
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
    TypeOfAny,
    TypeType,
    UnboundType,
    UnionType,
    get_proper_type,
)
from mypy.types import Type as MypyType

from . import protocols, signature_info


class TypeChecking:
    def __init__(self, *, resolver: protocols.Resolver) -> None:
        self.resolver = resolver

    def check_typeguard(self, ctx: MethodSigContext | FunctionSigContext) -> FunctionLike | None:
        info = signature_info.get_signature_info(ctx, self.resolver)
        if info is None:
            return None

        if info.is_guard and info.returns_concrete_annotation_with_type_var:
            # Mypy plugin system doesn't currently provide an opportunity to resolve a type guard when it's for a concrete annotation that uses a type var
            self.resolver.fail(
                "Can't use a TypeGuard that uses a Concrete Annotation that uses type variables"
            )

            if info.unwrapped_type_guard:
                return ctx.default_signature.copy_modified(type_guard=info.unwrapped_type_guard)

        return None

    def modify_return_type(self, ctx: MethodContext | FunctionContext) -> MypyType | None:
        info = signature_info.get_signature_info(ctx, self.resolver)
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


class _SharedConcreteAnnotationLogic:
    def __init__(
        self,
        make_resolver: protocols.ResolverMaker,
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
            return protocols.KnownAnnotations.resolve(ret_type.type.fullname) is not None
        else:
            return False

    def _type_checking(
        self, ctx: MethodContext | FunctionContext | MethodSigContext | FunctionSigContext
    ) -> TypeChecking:
        return TypeChecking(resolver=self.make_resolver(ctx=ctx))


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
