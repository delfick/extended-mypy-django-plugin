import dataclasses
from typing import TYPE_CHECKING, Generic, cast

from .. import protocols
from . import concrete_models, known_models, settings_types


@dataclasses.dataclass
class Discovery(Generic[protocols.T_Project]):
    discover_settings_types: protocols.SettingsTypesDiscovery[protocols.T_Project] = (
        dataclasses.field(default_factory=settings_types.NaiveSettingsTypesDiscovery)
    )
    discover_installed_models: protocols.InstalledModelsDiscovery[protocols.T_Project] = (
        dataclasses.field(default_factory=known_models.DefaultInstalledModulesDiscovery)
    )
    discover_concrete_models: protocols.ConcreteModelsDiscovery[protocols.T_Project] = (
        dataclasses.field(default_factory=concrete_models.ConcreteModelsDiscovery)
    )


if TYPE_CHECKING:
    _A: protocols.P_Discovery = cast(Discovery[protocols.P_Project], None)
