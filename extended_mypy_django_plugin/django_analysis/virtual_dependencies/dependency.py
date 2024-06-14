import dataclasses
import functools
from collections.abc import Callable, Mapping, Sequence
from typing import TYPE_CHECKING, Generic, TypedDict, cast

from typing_extensions import Self

from .. import project, protocols


@dataclasses.dataclass
class VirtualDependencySummary:
    virtual_dependency_name: protocols.ImportPath
    module_import_path: protocols.ImportPath
    installed_apps_hash: str | None
    significant_objects_hash: str | None


@dataclasses.dataclass
class VirtualDependency(Generic[protocols.T_Project]):
    module: protocols.Module
    interface_differentiator: str | None
    summary: VirtualDependencySummary
    all_related_models: Sequence[protocols.ImportPath]
    concrete_models: Mapping[protocols.ImportPath, Sequence[protocols.Model]]

    @classmethod
    def create(
        cls,
        *,
        discovered_project: protocols.Discovered[protocols.T_Project],
        module: protocols.Module,
        hasher: protocols.Hasher,
        virtual_dependency_namer: protocols.VirtualDependencyNamer,
        installed_apps_hash: str,
        make_differentiator: Callable[[], str],
    ) -> Self:
        if not module.installed:
            return cls.create_not_installed(
                discovered_project=discovered_project,
                module=module,
                virtual_dependency_namer=virtual_dependency_namer,
            )

        related_models: set[protocols.ImportPath] = set()
        custom_querysets: set[protocols.ImportPath] = set()
        for model in module.defined_models.values():
            related_models.add(model.import_path)
            if model.default_custom_queryset:
                custom_querysets.add(model.default_custom_queryset)
            for field in model.all_fields.values():
                if field.related_model:
                    related_models.add(field.related_model)

        return cls(
            module=module,
            interface_differentiator=make_differentiator(),
            summary=VirtualDependencySummary(
                virtual_dependency_name=virtual_dependency_namer(module.import_path),
                module_import_path=module.import_path,
                installed_apps_hash=installed_apps_hash,
                significant_objects_hash=hasher(
                    *(model.encode() for model in sorted(related_models | custom_querysets))
                ),
            ),
            all_related_models=sorted(related_models),
            concrete_models={
                import_path: discovered_project.concrete_models[import_path]
                for import_path in module.defined_models
            },
        )

    @classmethod
    def create_not_installed(
        cls,
        *,
        discovered_project: protocols.Discovered[protocols.T_Project],
        module: protocols.Module,
        virtual_dependency_namer: protocols.VirtualDependencyNamer,
    ) -> Self:
        return cls(
            module=module,
            interface_differentiator=None,
            summary=VirtualDependencySummary(
                virtual_dependency_name=virtual_dependency_namer(module.import_path),
                module_import_path=module.import_path,
                installed_apps_hash=None,
                significant_objects_hash=None,
            ),
            all_related_models=[],
            concrete_models={},
        )


if TYPE_CHECKING:
    C_VirtualDependency = VirtualDependency[project.C_Project]

    _VD: protocols.VirtualDependency = cast(VirtualDependency[protocols.P_Project], None)
    _VDS: protocols.VirtualDependencySummary = cast(VirtualDependencySummary, None)

    class _RequiredMakerKwargs(TypedDict):
        installed_apps_hash: str
        make_differentiator: Callable[[], str]

    _VDM: protocols.P_VirtualDependencyMaker = functools.partial(
        VirtualDependency[protocols.P_Project].create, **cast(_RequiredMakerKwargs, None)
    )

    _CVDM: protocols.VirtualDependencyMaker[project.C_Project, C_VirtualDependency] = (
        functools.partial(
            VirtualDependency[project.C_Project].create, **cast(_RequiredMakerKwargs, None)
        )
    )
