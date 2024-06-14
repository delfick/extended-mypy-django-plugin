import dataclasses
from typing import TYPE_CHECKING, Generic, cast

from .. import protocols


@dataclasses.dataclass
class Discovery(Generic[protocols.T_Project]):
    discover_settings_types: protocols.SettingsTypesDiscovery[protocols.T_Project]
    discover_installed_models: protocols.InstalledModelsDiscovery[protocols.T_Project]
    discover_concrete_models: protocols.ConcreteModelsDiscovery[protocols.T_Project]


if TYPE_CHECKING:
    _A: protocols.P_Discovery = cast(Discovery[protocols.P_Project], None)
