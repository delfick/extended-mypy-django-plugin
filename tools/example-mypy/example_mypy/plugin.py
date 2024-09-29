from extended_mypy_django_plugin.plugin import ExtendedMypyStubs, hook, protocols
from mypy import errorcodes
from mypy.checker import TypeChecker
from mypy.nodes import MemberExpr
from mypy.plugin import AttributeContext
from mypy.types import Type as MypyType
from mypy_django_plugin.lib import fullnames

from . import logic


class ExampleMypyPlugin(ExtendedMypyStubs[protocols.Report]):
    """
    Ensure that mypy understands django-configurations
    """

    @hook.hook
    class get_attribute_hook(
        hook.HookWithExtra["ExampleMypyPlugin", AttributeContext, None, MypyType]
    ):
        """
        We use this hook to resolve types of attributes in settings classes.

        We know that all django settings classes are based off djangoexample.settings.base.Base,
        and so when we find an attribute on django settings, we find the type on that class
        and use that.
        """

        def choose(
            self, *, fullname: str, super_hook: hook.MypyHook[AttributeContext, MypyType]
        ) -> hook.Choice[None]:
            class_name, _ = fullname.rsplit(".", 1)
            if class_name != fullnames.DUMMY_SETTINGS_BASE_CLASS:
                return False

            return True, None

        def run(
            self,
            ctx: AttributeContext,
            *,
            fullname: str,
            super_hook: hook.MypyHook[AttributeContext, MypyType],
            extra: None,
        ) -> MypyType:
            # Generally we will be passed a MemberExpr if the setting is being accessed directly
            # (e.g. settings.FOO), but sometimes we will be passed an anonymous Any context if the access
            # is through a hasattr call.
            #
            # See https://github.com/typeddjango/django-stubs/pull/1239 for more context
            if isinstance(ctx.context, MemberExpr):
                assert isinstance(ctx.api, TypeChecker)

                setting_name = ctx.context.name

                # SYL is our playground territory and this setting doesn't exist
                if setting_name == "SYL_BOTTLED_WATER_SHIPPING_CONFIG":
                    return ctx.api.named_type("builtins.str")

                def fail(msg: str, code: errorcodes.ErrorCode | None = None) -> None:
                    """
                    Shortcut to use the fail function without passing around ctx.api and ctx.context
                    """
                    ctx.api.fail(msg, ctx.context, code=code)

                resolved = logic.SettingsResolver.resolve(
                    setting_name=ctx.context.name,
                    fail=fail,
                    modules=ctx.api.modules,
                    django_context=self.plugin.django_context,
                )
                if resolved:
                    return resolved

                if resolved is False:
                    # We found the setting, but couldn't determine the type
                    assert isinstance(ctx.api, TypeChecker)
                    ctx.api.handle_cannot_determine_type(ctx.context.name, ctx.context)

            # Fallback to whatever django-stubs would do
            if super_hook:
                return super_hook(ctx)
            else:
                return ctx.default_attr_type
