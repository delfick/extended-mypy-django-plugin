from mypy.plugin import AnalyzeTypeContext
from mypy.types import ProperType, TypeType, TypeVarType, UnionType, get_proper_type
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
