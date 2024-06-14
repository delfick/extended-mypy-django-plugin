import dataclasses
from typing import TYPE_CHECKING, Generic, cast

from .. import protocols


@dataclasses.dataclass
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
            if name.startswith("_") or not name.isupper():
                continue

            result[name] = self.type_from_setting(loaded_project, name, getattr(settings, name))

        return result

    def type_from_setting(
        self, loaded_project: protocols.Loaded[protocols.T_Project], name: str, value: object
    ) -> str:
        return str(type(value))


if TYPE_CHECKING:
    _STA: protocols.P_SettingsTypesDiscovery = cast(
        NaiveSettingsTypesDiscovery[protocols.P_Project], None
    )
