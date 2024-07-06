from mypy.plugin import AnalyzeTypeContext
from mypy.types import Type as MypyType
from mypy.types import TypeQuery, TypeVarType, get_proper_type

from . import protocols


class HasTypeVars(TypeQuery[bool]):
    """
    Find where we have a concrete annotation
    """

    def __init__(self) -> None:
        super().__init__(any)

    def visit_type_var(self, t: TypeVarType) -> bool:
        return True


class Analyzer:
    def __init__(self, make_resolver: protocols.ResolverMaker) -> None:
        self.make_resolver = make_resolver

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

        if model_type.accept(HasTypeVars()):
            ctx.api.fail(
                "Using a concrete annotation on a TypeVar is not currently supported", ctx.context
            )
            return ctx.type

        resolved = resolver.resolve(annotation, model_type)
        if resolved is None:
            return ctx.type
        else:
            return resolved
