import dataclasses
from typing import TYPE_CHECKING, cast

from .. import protocols


@dataclasses.dataclass
class SettingsTypesAnalyzer:
    """
    The default implementation is a little naive and is only able to rely on inspecting
    the values on the settings object.
    """

    def __call__(self, loaded_project: protocols.LoadedProject, /) -> protocols.SettingsTypesMap:
        result: dict[str, str] = {}
        settings = loaded_project.settings

        for name in dir(settings):
            if name.startswith("_") or not name.isupper():
                continue

            result[name] = str(type(getattr(settings, name)))

        return result


if TYPE_CHECKING:
    _STA: protocols.SettingsTypesAnalyzer = cast(SettingsTypesAnalyzer, None)
