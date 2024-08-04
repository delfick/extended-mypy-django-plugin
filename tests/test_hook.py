import types
from unittest import mock

from mypy.options import Options
from mypy.plugin import AttributeContext, Plugin
from mypy.types import AnyType, TypeOfAny
from mypy.types import Type as MypyType

from extended_mypy_django_plugin.plugin import hook


class TestHookAndDecorator:
    def test_it_caches_instances_of_the_hook_class(self) -> None:
        result = AnyType(TypeOfAny.from_error)
        called: list[object] = []

        class MyPlugin(Plugin):
            @hook.hook
            class get_attribute_hook(hook.Hook["MyPlugin", AttributeContext, MypyType]):
                def hook(self, fullname: str) -> hook.MypyHook[AttributeContext, MypyType]:
                    called.append(
                        ("hook", self, fullname, self.plugin, self.super_hook_maker(fullname))
                    )
                    return self.run

                def run(self, ctx: AttributeContext) -> MypyType:
                    called.append(("run", self, ctx))
                    return result

        options = Options()
        plugin = MyPlugin(options)
        assert called == []

        descriptor = MyPlugin.get_attribute_hook
        assert isinstance(descriptor, hook.hook)

        assert descriptor._hook_instance is None
        hk = plugin.get_attribute_hook("one")
        assert isinstance(hk, types.MethodType)

        hook_instance = MyPlugin.get_attribute_hook._hook_instance
        assert hk.__self__ is hook_instance
        assert hk == hook_instance.run

        assert called == [("hook", hook_instance, "one", plugin, None)]

        called.clear()
        ctx = mock.Mock(spec=AttributeContext)
        assert hk(ctx) is result
        assert called == [("run", hook_instance, ctx)]

        # And when we call it again, we use the same hook instance
        called.clear()
        hk2 = plugin.get_attribute_hook("two")
        assert isinstance(hk2, types.MethodType)

        assert MyPlugin.get_attribute_hook._hook_instance is hook_instance
        assert hk2.__self__ is hook_instance
        assert hk2 == hook_instance.run

        assert called == [("hook", hook_instance, "two", plugin, None)]

        called.clear()
        ctx = mock.Mock(spec=AttributeContext)
        assert hk2(ctx) is result
        assert called == [("run", hook_instance, ctx)]
