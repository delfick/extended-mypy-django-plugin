import dataclasses
from typing import TYPE_CHECKING, cast

from .. import protocols


@dataclasses.dataclass
class Analyzers:
    analyze_known_models: protocols.KnownModelsAnalayzer
    analyze_settings_types: protocols.SettingsTypesAnalyzer


if TYPE_CHECKING:
    _A: protocols.Analyzers = cast(Analyzers, None)
