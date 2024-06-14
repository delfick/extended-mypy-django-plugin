import dataclasses
from typing import TYPE_CHECKING, cast

from .. import protocols


@dataclasses.dataclass
class Discovery:
    discover_settings_types: protocols.SettingsTypesDiscovery
    discover_installed_models: protocols.InstalledModelsDiscovery


if TYPE_CHECKING:
    _A: protocols.Discovery = cast(Discovery, None)
