import dataclasses
from typing import TYPE_CHECKING, cast

from .. import protocols


@dataclasses.dataclass
class SettingsTypesAnalyzer:
    def __call__(self, loaded_project: protocols.LoadedProject, /) -> protocols.SettingsTypesMap:
        raise NotImplementedError()


if TYPE_CHECKING:
    _STA: protocols.SettingsTypesAnalyzer = cast(SettingsTypesAnalyzer, None)
