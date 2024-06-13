import dataclasses
import inspect
import types
from collections import defaultdict
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Protocol, cast

from django.db import models

from .. import protocols


class ModuleCreator(Protocol):
    def __call__(
        self,
        *,
        import_path: protocols.ImportPath,
        module: types.ModuleType | None,
        models: Sequence[type[models.Model]],
    ) -> protocols.Module: ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class KnownModelsAnalyzer:
    module_creator: ModuleCreator

    def __call__(self, loaded_project: protocols.LoadedProject, /) -> protocols.ModelModulesMap:
        found: dict[protocols.ImportPath, list[type[models.Model]]] = defaultdict(list)
        for concrete_model_cls in loaded_project.apps.get_models():
            found[protocols.ImportPath(concrete_model_cls.__module__)].append(concrete_model_cls)

        result: dict[protocols.ImportPath, protocols.Module] = {}

        for module_import_path, module_models in found.items():
            module = inspect.getmodule(module_models[0])
            if module is None:
                raise RuntimeError("Failed to determine the module these models appear in")

            entity = self.module_creator(
                import_path=module_import_path, module=module, models=module_models
            )
            result[module_import_path] = entity

        for app in loaded_project.apps.get_app_configs():

            def _compat_models_module_is_module_type(
                models_module: Any,
            ) -> types.ModuleType | None:
                # older version of django-stubs typed this wrong
                return models_module  # type: ignore[no-any-return]

            if models_module := _compat_models_module_is_module_type(app.models_module):
                import_path = protocols.ImportPath(models_module.__name__)
                if import_path not in result:
                    result[import_path] = self.module_creator(
                        import_path=import_path, module=models_module, models=[]
                    )

        return result


if TYPE_CHECKING:
    _KMA: protocols.KnownModelsAnalayzer = cast(KnownModelsAnalyzer, None)
