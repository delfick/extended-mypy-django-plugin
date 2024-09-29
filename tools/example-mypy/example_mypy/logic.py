from typing import Literal

import attrs
from extended_mypy_django_plugin.plugin import protocols
from mypy import errorcodes
from mypy.nodes import MypyFile, SymbolTable, TypeInfo
from mypy.types import CallableType, UnboundType
from mypy.types import Type as MypyType
from mypy_django_plugin.django.context import DjangoContext


@attrs.define
class SettingsResolver:
    """
    Resolve a type for a django setting based on the type for that setting in
    djangoexample.settings.base.Base, which is the root parent class for settings
    """

    fail: protocols.FailFunc
    setting_name: str
    base_settings: TypeInfo

    @classmethod
    def resolve(
        cls,
        setting_name: str,
        fail: protocols.FailFunc,
        modules: dict[str, MypyFile],
        django_context: DjangoContext,
    ) -> MypyType | Literal[False] | None:
        base_module = modules.get("djangoexample.settings.base")
        if not isinstance(base_module, MypyFile):
            # this is one of those "shouldn't happen" errors
            fail("Failed to lookup the type for djangoexample.settings.base")
            return None

        Base = base_module.names.get("Base")
        if Base is None or not isinstance(Base.node, TypeInfo):
            # this is one of those "shouldn't happen" errors
            fail("Failed to lookup the type for djangoexample.settings.base.Base")
            return None

        if not hasattr(django_context.settings, setting_name):
            # This can't return an ATTR_DEFINED error, because it will be overridden by what django-stubs does
            fail(f"'Settings' object has no attribute {setting_name!r}")
            return None

        return cls(fail=fail, setting_name=setting_name, base_settings=Base.node)._resolve()

    def _resolve(self) -> MypyType | Literal[False] | None:
        setting = self.base_settings.names.get(self.setting_name)

        if setting is None:
            if self.setting_name in ("LANGUAGES", "TIME_ZONE", "LANGUAGE_COOKIE_NAME"):
                # These are valid settings defined by Django itself but are not on base.Base
                return None

            self.fail(
                f"Could not find settings.{self.setting_name} on djangoexample.settings.base.Base",
                code=errorcodes.ATTR_DEFINED,
            )
            return None

        setting_type: MypyType | Literal[False] = False

        if isinstance(setting.type, CallableType):
            setting_type = setting.type.ret_type
        elif setting.type and not isinstance(setting.type, UnboundType):
            setting_type = setting.type

        return setting_type
