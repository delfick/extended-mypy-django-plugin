from mypy.nodes import GDEF, AssignmentStmt, NameExpr, SymbolTableNode
from mypy.plugin import AnalyzeTypeContext, DynamicClassDefContext
from mypy.semanal import SemanticAnalyzer
from mypy.types import Instance, ProperType, TypeType, TypeVarType, UnionType, get_proper_type
from mypy.types import Type as MypyType

from . import protocols


class Analyzer:
    def __init__(self, make_resolver: protocols.ResolverMaker) -> None:
        self.make_resolver = make_resolver

    def _has_typevars(self, the_type: ProperType) -> bool:
        if isinstance(the_type, TypeType):
            the_type = the_type.item

        if isinstance(the_type, TypeVarType):
            return True

        if not isinstance(the_type, UnionType):
            return False

        return any(self._has_typevars(get_proper_type(item)) for item in the_type.items)

    def analyze_type(
        self, ctx: AnalyzeTypeContext, annotation: protocols.KnownAnnotations
    ) -> MypyType:
        """
        We resolve annotations at this point. Unless the type being analyzed involves type vars.

        Resolving type vars requires we wait until we are analyzing method/function calls. Between now
        and then we replace the type with an unbound type that wraps a resolved instance because when we
        can resolve the type vars we can't resolve what the type var actually is!
        """
        args = ctx.type.args
        if len(args) != 1:
            ctx.api.fail("Concrete annotations must contain exactly one argument", ctx.context)
            return ctx.type

        model_type = get_proper_type(ctx.api.analyze_type(args[0]))

        resolver = self.make_resolver(ctx=ctx)

        if self._has_typevars(model_type):
            # We don't have the information to resolve type vars at this point
            # We wrap the result so that we can continue this later without mypy
            # being sad about how Concrete doesn't match what we resolve it to in the end
            wrapped = resolver.rewrap_concrete_type(model_type=model_type, annotation=annotation)
            return ctx.type if wrapped is None else wrapped

        resolved = resolver.resolve(annotation, model_type)
        if resolved is None:
            return ctx.type
        else:
            return resolved

    def transform_type_var_classmethod(self, ctx: DynamicClassDefContext) -> None:
        if len(ctx.call.args) != 2:
            ctx.api.fail("Concrete.type_var takes exactly two arguments", ctx.call)
            return None

        # We need much more than is on the interface unfortunately
        assert isinstance(ctx.api, SemanticAnalyzer)
        sem_api = ctx.api

        inside: str | None = None
        if ctx.api.scope.classes and ctx.api.scope.functions:
            inside = "method scope"
        elif ctx.api.scope.classes:
            inside = "class scope"
        elif ctx.api.scope.functions:
            inside = "function scope"

        if inside:
            # We modify the module scope in this hook, so make sure it's in module scope!
            ctx.api.fail(
                f"Can only use Concrete.type_var at module scope, rather than {inside}", ctx.call
            )
            return None

        # This copies what mypy does to resolve TypeVars
        # https://github.com/python/mypy/blob/v1.10.1/mypy/semanal.py#L4234
        name = sem_api.extract_typevarlike_name(
            AssignmentStmt([NameExpr(ctx.name)], ctx.call.callee), ctx.call
        )
        if name is None:
            return None

        second_arg = ctx.call.args[1]
        parent_type = get_proper_type(sem_api.expr_to_analyzed_type(second_arg))

        if not isinstance(parent_type, Instance):
            if ctx.api.final_iteration:
                ctx.api.fail(f"Failed to locate the model provided: {ctx.name}", ctx.call)
            else:
                ctx.api.defer()

            return None

        type_var_expr = self.make_resolver(ctx=ctx).type_var_expr_for(
            model=parent_type.type,
            name=name,
            fullname=f"{ctx.api.cur_mod_id}.{name}",
            object_type=ctx.api.named_type("builtins.object"),
        )

        # Note that we will override even if we've already generated the type var
        # because it's possible for a first pass to have no values but a second to do have values
        # And in between that we do need this to be a typevar expr
        module = ctx.api.modules[ctx.api.cur_mod_id]
        module.names[name] = SymbolTableNode(GDEF, type_var_expr, plugin_generated=True)
        return None
