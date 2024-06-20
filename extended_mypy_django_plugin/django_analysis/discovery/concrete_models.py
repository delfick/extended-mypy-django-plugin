import dataclasses
from typing import TYPE_CHECKING, Generic, cast

from .. import protocols


@dataclasses.dataclass(frozen=True, kw_only=True)
class ConcreteModelsDiscovery(Generic[protocols.T_Project]):
    """
    The default implementation that determines the concrete models for each model.

    For abstract models, this is all the concrete children.

    For concrete models, this is the model by itself.
    """

    def __call__(
        self,
        loaded_project: protocols.Loaded[protocols.T_Project],
        all_models: protocols.ModelMap,
        /,
    ) -> protocols.ConcreteModelsMap:
        result: dict[protocols.ImportPath, list[protocols.ImportPath]] = {}

        for import_path, model in all_models.items():
            if model.is_abstract:
                if import_path not in result:
                    result[import_path] = []
                continue

            result[import_path] = [model.import_path]
            for mro_import_path in model.models_in_mro:
                found = all_models[mro_import_path]
                if found.is_abstract:
                    if mro_import_path not in result:
                        result[mro_import_path] = []
                    result[mro_import_path].append(import_path)

        return {
            import_path: [all_models[path] for path in concrete]
            for import_path, concrete in result.items()
        }


if TYPE_CHECKING:
    _STA: protocols.P_ConcreteModelsDiscovery = cast(
        ConcreteModelsDiscovery[protocols.P_Project], None
    )
