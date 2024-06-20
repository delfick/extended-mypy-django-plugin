import dataclasses
from typing import TYPE_CHECKING, Generic, cast

from .. import protocols


@dataclasses.dataclass(frozen=True, kw_only=True)
class NaiveSettingsTypesDiscovery(Generic[protocols.T_Project]):
    """
    The default implementation is a little naive and is only able to rely on inspecting
    the values on the settings object.
    """

    def __call__(
        self, loaded_project: protocols.Loaded[protocols.T_Project], /
    ) -> protocols.SettingsTypesMap:
        result: dict[str, str] = {}
        settings = loaded_project.settings

        for name in dir(settings):
            if not self.valid_setting_name(loaded_project=loaded_project, name=name):
                continue

            result[name] = self.type_from_setting(
                loaded_project=loaded_project, name=name, value=getattr(settings, name)
            )

        return result

    def valid_setting_name(
        self, *, loaded_project: protocols.Loaded[protocols.T_Project], name: str
    ) -> bool:
        return not name.startswith("_") and name.isupper()

    def type_from_setting(
        self, *, loaded_project: protocols.Loaded[protocols.T_Project], name: str, value: object
    ) -> str:
        return str(type(value))


if TYPE_CHECKING:
    _STA: protocols.P_SettingsTypesDiscovery = cast(
        NaiveSettingsTypesDiscovery[protocols.P_Project], None
    )
