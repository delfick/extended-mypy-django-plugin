import dataclasses
import functools
from collections.abc import Iterator, Sequence
from typing import TYPE_CHECKING, Generic, TypedDict, cast

from typing_extensions import Self

from .. import project, protocols


@dataclasses.dataclass
class VirtualDependencySummary:
    virtual_namespace: protocols.ImportPath
    virtual_import_path: protocols.ImportPath
    module_import_path: protocols.ImportPath
    significant_info: Sequence[str]


@dataclasses.dataclass
class VirtualDependency(Generic[protocols.T_Project]):
    module: protocols.Module
    summary: VirtualDependencySummary
    all_related_models: Sequence[protocols.ImportPath]
    concrete_models: protocols.ConcreteModelsMap

    @classmethod
    def create(
        cls,
        *,
        discovered_project: protocols.Discovered[protocols.T_Project],
        module: protocols.Module,
        virtual_dependency_namer: protocols.VirtualDependencyNamer,
    ) -> Self:
        concrete_models = {
            import_path: discovered_project.concrete_models[import_path]
            for import_path in module.defined_models
        }

        related_models: set[protocols.ImportPath] = set()
        for model in module.defined_models.values():
            related_models.add(model.import_path)
            for field in model.all_fields.values():
                if field.related_model:
                    related_models.add(field.related_model)

        return cls(
            module=module,
            summary=VirtualDependencySummary(
                virtual_namespace=virtual_dependency_namer.namespace,
                virtual_import_path=virtual_dependency_namer(module.import_path),
                module_import_path=module.import_path,
                significant_info=list(
                    cls.find_significant_info_from_module(
                        discovered_project=discovered_project,
                        module=module,
                        concrete_models=concrete_models,
                    )
                ),
            ),
            all_related_models=sorted(related_models),
            concrete_models=concrete_models,
        )

    @classmethod
    def find_significant_info_from_module(
        cls,
        *,
        discovered_project: protocols.Discovered[protocols.T_Project],
        module: protocols.Module,
        concrete_models: protocols.ConcreteModelsMap,
    ) -> Iterator[str]:
        prefix = f"module:{module.import_path}"
        yield prefix
        for model_import_path, concrete_children in concrete_models.items():
            yield f"{prefix}>concrete:{model_import_path}={','.join(conc.import_path for conc in concrete_children)}"

        for model in module.defined_models.values():
            for info in cls.find_significant_info_from_model(
                discovered_project=discovered_project, module=module, model=model
            ):
                yield f"{prefix}>{info}"

    @classmethod
    def find_significant_info_from_model(
        cls,
        *,
        discovered_project: protocols.Discovered[protocols.T_Project],
        module: protocols.Module,
        model: protocols.Model,
    ) -> Iterator[str]:
        model_prefix = f"model:{model.import_path}"
        yield f"{model_prefix}>is_abstract:{model.is_abstract}"

        if model.default_custom_queryset:
            yield f"{model_prefix}>custom_queryset:{model.default_custom_queryset}"

        for i, mro_import_path in enumerate(model.models_in_mro):
            yield f"{model_prefix}>mro_{i}:{mro_import_path}"

        for name, field in model.all_fields.items():
            field_prefix = f"{model_prefix}>field:{name}"
            yield field_prefix
            for info in cls.find_significant_info_from_field(
                discovered_project=discovered_project, module=module, model=model, field=field
            ):
                yield f"{field_prefix}>{info}"

    @classmethod
    def find_significant_info_from_field(
        cls,
        *,
        discovered_project: protocols.Discovered[protocols.T_Project],
        module: protocols.Module,
        model: protocols.Model,
        field: protocols.Field,
    ) -> Iterator[str]:
        yield f"field_type:{field.field_type}"
        if field.related_model:
            yield f"related_model:{field.related_model}"


if TYPE_CHECKING:
    C_VirtualDependency = VirtualDependency[project.C_Project]

    _VD: protocols.VirtualDependency = cast(VirtualDependency[protocols.P_Project], None)
    _VDS: protocols.VirtualDependencySummary = cast(VirtualDependencySummary, None)

    class _RequiredMakerKwargs(TypedDict):
        virtual_dependency_namer: protocols.VirtualDependencyNamer

    _VDM: protocols.P_VirtualDependencyMaker = functools.partial(
        VirtualDependency[protocols.P_Project].create, **cast(_RequiredMakerKwargs, None)
    )

    _CVDM: protocols.VirtualDependencyMaker[project.C_Project, C_VirtualDependency] = (
        functools.partial(
            VirtualDependency[project.C_Project].create, **cast(_RequiredMakerKwargs, None)
        )
    )
