import dataclasses
from typing import TYPE_CHECKING, cast

from .. import protocols


@dataclasses.dataclass
class KnownModelsAnalyzer:
    def __call__(self, loaded_project: protocols.LoadedProject, /) -> protocols.ModelModulesMap:
        raise NotImplementedError()


if TYPE_CHECKING:
    _KMA: protocols.KnownModelsAnalayzer = cast(KnownModelsAnalyzer, None)
