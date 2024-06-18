import dataclasses
import functools
import importlib
import inspect
import types
from collections import defaultdict
from collections.abc import Iterator, Sequence
from typing import TYPE_CHECKING, Any, Generic, Protocol, cast

from django.db import models

from .. import protocols
from .import_path import ImportPath


class ModuleCreator(Protocol):
    def __call__(
        self,
        *,
        import_path: protocols.ImportPath,
        module: types.ModuleType | None,
        models: Sequence[type[models.Model]],
    ) -> protocols.Module: ...


def make_module_creator() -> ModuleCreator:
    from extended_mypy_django_plugin import django_analysis

    field_creator = django_analysis.Field.create
    model_creator = functools.partial(django_analysis.Model.create, field_creator=field_creator)
    return functools.partial(django_analysis.Module.create, model_creator=model_creator)


@dataclasses.dataclass(frozen=True, kw_only=True)
class DefaultInstalledModulesDiscovery(Generic[protocols.T_Project]):
    module_creator: ModuleCreator = dataclasses.field(default_factory=make_module_creator)

    def __call__(
        self, loaded_project: protocols.Loaded[protocols.T_Project], /
    ) -> protocols.ModelModulesMap:
        found: dict[protocols.ImportPath, list[type[models.Model]]] = defaultdict(list)
        for concrete_model_cls in loaded_project.apps.get_models():
            found[ImportPath.cls_module(concrete_model_cls)].append(concrete_model_cls)

        result: dict[protocols.ImportPath, protocols.Module] = {}

        for module_import_path, module_models in found.items():
            module = inspect.getmodule(module_models[0])
            if module is None:
                raise RuntimeError("Failed to determine the module these models appear in")

            entity = self.module_creator(
                import_path=module_import_path,
                module=module,
                models=[*self._find_abstract_models(module), *module_models],
            )
            result[module_import_path] = entity

        for app in loaded_project.apps.get_app_configs():

            def _compat_models_module_is_module_type(
                models_module: Any,
            ) -> types.ModuleType | None:
                # older version of django-stubs typed this wrong
                return models_module  # type: ignore[no-any-return]

            if models_module := _compat_models_module_is_module_type(app.models_module):
                import_path = ImportPath.from_module(models_module)
                if import_path not in result:
                    result[import_path] = self.module_creator(
                        import_path=import_path,
                        module=models_module,
                        models=list(self._find_abstract_models(models_module)),
                    )

        changed: bool = True
        while changed:
            changed = self._find_non_direct_modules(result)

        return result

    def _find_non_direct_modules(
        self, result: dict[protocols.ImportPath, protocols.Module]
    ) -> bool:
        changed: bool = False
        for module in list(result.values()):
            for model in module.defined_models.values():
                for mro_model in model.models_in_mro:
                    if (
                        module_import_path := ImportPath(mro_model.rsplit(".", 1)[0])
                    ) not in result:
                        changed = True
                        module = importlib.import_module(str(module_import_path))
                        result[module_import_path] = self.module_creator(
                            import_path=module_import_path,
                            module=module,
                            models=list(self._find_all_models(module)),
                        )

        return changed

    def _find_all_models(self, module: types.ModuleType) -> Iterator[type[models.Model]]:
        for attr in dir(module):
            val = getattr(module, attr)
            if isinstance(val, type) and issubclass(val.__class__, models.base.ModelBase):
                if val.__module__ != module.__name__:
                    continue

                yield val

    def _find_abstract_models(self, module: types.ModuleType) -> Iterator[type[models.Model]]:
        for model in self._find_all_models(module):
            if hasattr(model, "_meta") and getattr(model._meta, "abstract", False):
                yield model


if TYPE_CHECKING:
    _KMA: protocols.P_InstalledModelsDiscovery = cast(
        DefaultInstalledModulesDiscovery[protocols.P_Project], None
    )
