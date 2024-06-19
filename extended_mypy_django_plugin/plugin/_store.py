import importlib.metadata
from collections.abc import Iterator, Mapping, Sequence
from typing import Protocol

from django.db import models
from mypy.nodes import SymbolTableNode, TypeInfo
from mypy.types import Instance, UnionType, get_proper_type

from ._reports import FieldRelatedModelClsGetter, ModelModules, ModelRelatedFieldsGetter, Reports

MODEL_CLASS_FULLNAME = "django.db.models.base.Model"

QUERYSET_CLASS_FULLNAME = "django.db.models.query.QuerySet"
if importlib.metadata.version("mypy") == "1.4.0":
    QUERYSET_CLASS_FULLNAME = "django.db.models.query._QuerySet"


class UnionMustBeOfTypes(Exception):
    pass


class RestartDmypy(Exception):
    pass


class LookupInfo(Protocol):
    def __call__(self, fullname: str) -> TypeInfo | None: ...


class LookupNode(Protocol):
    def __call__(self, fullname: str) -> SymbolTableNode | None: ...


class LookupInstanceFunction(Protocol):
    def __call__(self, fullname: str) -> Instance | None: ...


class GetModelClassByFullname(Protocol):
    def __call__(self, fullname: str) -> type[models.Model] | None: ...


class IsInstalledModel(Protocol):
    def __call__(self, *, import_path: str) -> bool: ...


class KnownConcreteModelsGetter(Protocol):
    def __call__(self, fullname: str) -> set[str]: ...


class Store:
    """
    The store is used to interrogate the metadata on ``TypeInfo`` objects to determine
    the available concrete models and queryset objects when resolving the annotations
    this plugin provides.

    .. automethod:: retrieve_concrete_children_types

    .. automethod:: realise_querysets
    """

    def __init__(
        self,
        report: Reports,
        installed_apps: list[str],
        get_model_related_fields: ModelRelatedFieldsGetter,
        get_field_related_model_cls: FieldRelatedModelClsGetter,
        get_model_class_by_fullname: GetModelClassByFullname,
        lookup_info: LookupInfo,
        lookup_fully_qualified: LookupNode,
        django_context_model_modules: Mapping[str, object],
        is_installed_model: IsInstalledModel,
        known_concrete_models: KnownConcreteModelsGetter,
    ) -> None:
        self._get_model_class_by_fullname = get_model_class_by_fullname
        self._django_context_model_modules = django_context_model_modules
        self._is_installed_model = is_installed_model
        self._known_concrete_models = known_concrete_models

        self.plugin_lookup_info = lookup_info
        self.plugin_lookup_fully_qualified = lookup_fully_qualified

        self.model_modules = self._determine_model_modules()

        # Still need to generate the old reports until this store has been removed
        report.report_names_getter(
            installed_apps=installed_apps,
            model_modules=self.model_modules,
            get_model_related_fields=get_model_related_fields,
            get_field_related_model_cls=get_field_related_model_cls,
        )

    def retrieve_concrete_children_types(
        self,
        parent: TypeInfo,
        lookup_info: LookupInfo,
        lookup_instance: LookupInstanceFunction,
    ) -> Sequence[Instance]:
        """
        Given a ``TypeInfo`` representing some model, return ``MypyType`` objects
        for all the concrete children related to the specified model.
        """
        values: list[Instance] = []

        concrete_type_infos = self._retrieve_concrete_children_info_from_metadata(
            parent, lookup_info
        )
        for info in concrete_type_infos:
            instance = lookup_instance(info.fullname)
            if instance and self._is_installed_model(import_path=instance.type.fullname):
                values.append(instance)

        return values

    def realise_querysets(
        self, type_var: Instance | UnionType, lookup_info: LookupInfo
    ) -> Iterator[Instance]:
        """
        Given either a specific model, or a union of models, return the
        default querysets for those models.
        """
        querysets = self._get_queryset_fullnames(type_var, lookup_info)
        for fullname, model in querysets:
            queryset = lookup_info(fullname)
            if not queryset:
                raise RestartDmypy(f"Could not find queryset for {fullname}")

            if not queryset.is_generic():
                yield Instance(queryset, [])
            else:
                yield Instance(
                    queryset,
                    [Instance(model, []) for _ in range(len(queryset.type_vars))],
                )

    def _determine_model_modules(self) -> ModelModules:
        """
        Old version of django-stubs has this as a different datastructure
        """
        result: dict[str, dict[str, type[models.Model]]] = {}
        for k, v in self._django_context_model_modules.items():
            if isinstance(v, dict):
                result[k] = v
            elif isinstance(v, set):
                result[k] = {
                    cls.__name__: cls
                    for cls in v
                    if isinstance(cls, type) and issubclass(cls, models.Model)
                }
        return result

    def _retrieve_concrete_children_info_from_metadata(
        self, parent: TypeInfo, lookup_info: LookupInfo
    ) -> Sequence[TypeInfo]:
        """
        For the children recorded in the metadata for this model, return those
        that aren't abstract
        """
        children = sorted(self._known_concrete_models(parent.fullname))

        ret: list[TypeInfo] = []
        for child in children:
            info = lookup_info(child)
            if not info:
                continue

            abstract: bool = False
            if "django" not in info.metadata:
                # Old versions of mypy/django-stubs don't have metadata at this point
                model_cls = self._get_model_class_by_fullname(info.fullname)
                abstract = bool(model_cls and model_cls._meta.abstract)
            else:
                abstract = info.metadata.get("django", {}).get("is_abstract_model", False)

            if not abstract:
                ret.append(info)

        return ret

    def _get_queryset_fullnames(
        self, type_var: Instance | UnionType, lookup_info: LookupInfo
    ) -> Iterator[tuple[str, TypeInfo]]:
        """
        Return the fullnames of the default querysets for the models represented
        by this instance or Union of instances.
        """
        children: list[TypeInfo] = []
        if isinstance(type_var, UnionType):
            for item in type_var.items:
                item = get_proper_type(item)
                if not isinstance(item, Instance):
                    raise UnionMustBeOfTypes()
                children.append(item.type)
        else:
            children.append(type_var.type)

        for child in children:
            yield (
                self._get_dynamic_queryset_fullname(child, lookup_info) or QUERYSET_CLASS_FULLNAME,
                child,
            )

    def _get_dynamic_manager(self, model: TypeInfo, lookup_info: LookupInfo) -> TypeInfo | None:
        """
        For some model return a custom manager if one exists
        """
        model_cls = self._get_model_class_by_fullname(model.fullname)
        if model_cls is None:
            raise RestartDmypy(f"Could not find model class for {model.fullname}")

        manager = model_cls._default_manager
        if manager is None:
            return None

        if not isinstance(manager, models.Manager):
            return None

        manager_fullname = manager.__class__.__module__ + "." + manager.__class__.__qualname__
        manager_info = lookup_info(manager_fullname)
        if manager_info is None:
            base_manager_class = manager.__class__.__bases__[0]
            base_manager_fullname = (
                base_manager_class.__module__ + "." + base_manager_class.__qualname__
            )

            base_manager_info = lookup_info(base_manager_fullname)
            if not base_manager_info:
                raise RestartDmypy(f"Could not find base manager for {base_manager_fullname}")

            metadata = base_manager_info.metadata

            generated_managers: dict[str, str]
            if "from_queryset_managers" not in metadata:
                metadata["from_queryset_managers"] = {}
            generated_managers = {
                k: v for k, v in metadata["from_queryset_managers"].items() if isinstance(v, str)
            }

            generated_manager_name: str | None = generated_managers.get(manager_fullname)
            if generated_manager_name is None:
                return None

            manager_info = lookup_info(generated_manager_name)

        return manager_info

    def _get_dynamic_queryset_fullname(
        self, model: TypeInfo, lookup_info: LookupInfo
    ) -> str | None:
        """
        For this model, return the fullname of the custom queryset for the
        default manager if there is such a custom QuerySet.
        """
        dynamic_manager = self._get_dynamic_manager(model, lookup_info)
        if not dynamic_manager:
            model_cls = self._get_model_class_by_fullname(model.fullname)
            if (
                model_cls
                and hasattr(model_cls, "_default_manager")
                and isinstance(model_cls._default_manager, models.Manager)
                and hasattr(model_cls._default_manager, "_queryset_class")
            ):
                queryset = model_cls._default_manager._queryset_class
                if isinstance(queryset, type) and issubclass(queryset, models.QuerySet):
                    return queryset.__module__ + "." + queryset.__qualname__
            return None

        name = dynamic_manager.metadata["django"].get("from_queryset_manager")
        if name is not None and isinstance(name, str):
            assert isinstance(name, str)
            return name

        return None
