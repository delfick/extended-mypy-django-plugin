import dataclasses
import functools
import pathlib
from collections import defaultdict

import attrs
import django.db.models
from django.db.models.fields.related import ForeignKey
from extended_mypy_django_plugin import django_analysis
from extended_mypy_django_plugin.django_analysis import Loaded
from example_mypy.virtual_dependencies import VirtualDependencyHandler

PROJECT_ROOT = pathlib.Path(__file__).parent.parent


@attrs.define
class _Collector:
    """
    Used by the test below to record and report on what models/fields exist in
    our Django project
    """

    by_queryset_name: dict[str, set[django_analysis.protocols.ImportPath]] = attrs.field(
        factory=lambda: defaultdict(set)
    )

    model_to_queryset: dict[
        django_analysis.protocols.ImportPath, django_analysis.protocols.ImportPath | None
    ] = attrs.field(factory=dict)

    by_related_name: dict[str, set[django_analysis.protocols.ImportPath]] = attrs.field(
        factory=lambda: defaultdict(set)
    )

    def _by_import_path(self, path: str) -> str:
        mod, name = path.rsplit(".", 1)
        return f"djangoexample/{'/'.join(mod.split('.'))}.py   {name}"

    def field_creator(
        self,
        *,
        model_import_path: django_analysis.protocols.ImportPath,
        field: django_analysis.protocols.DjangoField,
    ) -> django_analysis.protocols.Field:
        """
        This is called for every field on every model, we use it to find which models are
        provided to other models with some specific related_name
        """
        if isinstance(field, ForeignKey) and (related_name := field.related_query_name()):
            related_name = related_name % {
                "app_label": field.model._meta.app_label,
                "class": field.model.__name__,
            }
            self.by_related_name[related_name].add(
                django_analysis.ImportPath.from_cls(field.model)
            )

        return django_analysis.Field.create(model_import_path=model_import_path, field=field)

    def model_creator(
        self, *, model: type[django.db.models.Model]
    ) -> django_analysis.protocols.Model:
        """
        This is called for every model, we use it to figure out the custom querysets
        each model have, and also find custom querysets that share the same name
        """
        created = django_analysis.Model.create(field_creator=self.field_creator, model=model)

        self.model_to_queryset[created.import_path] = created.default_custom_queryset
        if created.default_custom_queryset is not None:
            self.by_queryset_name[created.default_custom_queryset.split(".")[-1]].add(
                created.default_custom_queryset
            )

        return created

    def find_places_needing_attention(self) -> str | None:
        need_unique_names: list[str] = []
        need_custom_querysets: list[str] = []

        # Find where we have multiple querysets with the same name
        for name, found in self.by_queryset_name.items():
            if len(found) != 1:
                need_unique_names.append(name)
                for q in found:
                    need_unique_names.append(f"    {self._by_import_path(q)}")
                need_unique_names.append("")

        # Find where a related name has multiple models
        # Where there are multiple models with the same name and the associated
        # querysets are not unique
        for related_name, models in self.by_related_name.items():
            if related_name == "+":
                # Where the related name is a + isn't relevant to us here
                continue

            if any(
                model.startswith("django.") or model.startswith("wagtail.") for model in models
            ):
                # We can't do anything about django itself or where wagtail causes
                # this problem
                continue

            by_name = defaultdict(set)
            for model in models:
                by_name[model.split(".")[-1]].add(model)

            if not any(len(duplicate) > 1 for _, duplicate in by_name.items()):
                # no problem if there isn't multiple models with the same name
                # Where this has multiple models with the same name, they'll have
                # a different namespace
                continue

            for _, duplicate in by_name.items():
                qs = [self.model_to_queryset[m] for m in duplicate]
                if len(set(qs)) == len(qs):
                    # If the set of querysets is the same length as the list
                    # Then there are no duplicates!
                    continue

                # We found a related name with multiple models with querysets
                # that don't have unique names!
                need_custom_querysets.append(related_name)
                for m in duplicate:
                    need_custom_querysets.append(f"    {self._by_import_path(m)}")
                need_custom_querysets.append("")

        if need_unique_names:
            # Add a header for the output
            need_unique_names.insert(0, "----------------------------------------")
            need_unique_names.insert(0, "These custom querysets need unique names")

        if need_custom_querysets:
            # Add a header for the output
            need_custom_querysets.insert(0, "----------------------------------------------")
            need_custom_querysets.insert(0, "These models need to be given custom querysets")

        if not need_unique_names and not need_custom_querysets:
            # Nothing to report if there's nothing to report
            return None

        return "\n".join(["\n", *need_unique_names, "\n", *need_custom_querysets])


def main() -> None:
    collector = _Collector()

    # Create the object representing the project with a custom discoverer
    # That will record information about each model/field it comes across
    project = dataclasses.replace(
        VirtualDependencyHandler.make_project(
            project_root=PROJECT_ROOT, django_settings_module="djangoexample.settings"
        ),
        discovery=django_analysis.discovery.Discovery(
            discover_installed_models=django_analysis.discovery.DefaultInstalledModulesDiscovery(
                module_creator=functools.partial(
                    django_analysis.Module.create, model_creator=collector.model_creator
                )
            )
        ),
    )

    # Execute the discovery logic
    project.load_project().perform_discovery()

    # Determine if we need to complain about querysets that need unique names
    warning = collector.find_places_needing_attention()
    if warning:
        raise AssertionError(warning)


if __name__ == "__main__":
    main()
