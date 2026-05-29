import importlib.metadata

import packaging.version
from extended_mypy_django_plugin_test_driver import ScenarioBuilder


class TestHideQuerySetAnnotations:
    def test_ignoring_annotations(self, builder: ScenarioBuilder) -> None:
        @builder.run_and_check_after
        def _() -> None:
            builder.set_and_copy_installed_apps("leader", "follower1")
            builder.on("main.py").set(
                """
                from follower1 import models as f1models
                from django.db import models
                from extended_mypy_django_plugin import hide_queryset_annotations

                def not_using_helper() -> f1models.Follower1QuerySet[f1models.Follower1]:
                    qs = f1models.Follower1.objects.all()

                    return qs.annotate(value=models.Value(1)).filter(value=1)
                    # ^ ERROR(return-value) ^ Incompatible return value type (got "Follower1QuerySet[Follower1@AnnotatedWith[TypedDict({'value': Any})], Follower1@AnnotatedWith[TypedDict({'value': Any})]]", expected "Follower1QuerySet[Follower1]")

                def using_helper() -> f1models.Follower1QuerySet[f1models.Follower1]:
                    qs = f1models.Follower1.objects.all()
                    return hide_queryset_annotations(qs.annotate(value=models.Value(1)).filter(value=1))
                """
            )

    def test_retains_row_type(self, builder: ScenarioBuilder) -> None:
        stubs_version = packaging.version.Version(importlib.metadata.version("django-stubs"))
        if stubs_version < packaging.version.Version("6.0.2"):
            value_type = "dict[str, Any]"
            row_type = "dict[str, Any]"
        else:
            # It's not till the later django-stubs that it understands the value type correctly
            value_type = "TypedDict({'good': bool})"
            row_type = "_Row"

        @builder.run_and_check_after
        def _() -> None:
            builder.set_and_copy_installed_apps("leader", "follower1")
            builder.on("main.py").set(
                f"""
                from follower1 import models as f1models
                from django.db import models
                from typing import TypedDict, Any
                from extended_mypy_django_plugin import hide_queryset_annotations

                class _Row(TypedDict):
                    good: bool

                def returning_values() -> models.QuerySet[f1models.Follower1, {row_type}]:
                    qs = f1models.Follower1.objects.all()

                    annotated = qs.annotate(value=models.Value(1)).filter(value=1)
                    # ^ REVEAL ^ follower1.models.follower1.Follower1QuerySet[follower1.models.follower1.Follower1@AnnotatedWith[TypedDict({{'value': Any}})], follower1.models.follower1.Follower1@AnnotatedWith[TypedDict({{'value': Any}})]]
                    
                    with_values = annotated.values("good")
                    # ^ REVEAL ^ django.db.models.query.QuerySet[follower1.models.follower1.Follower1@AnnotatedWith[TypedDict({{'value': Any}})], {value_type}]

                    without_the_annotations = hide_queryset_annotations(with_values)
                    # ^ REVEAL ^ django.db.models.query.QuerySet[follower1.models.follower1.Follower1, {value_type}]

                    return with_values
                    # it seems django-stubs already is fine with this
                """
            )

    def test_works_on_non_custom_querysets(self, builder: ScenarioBuilder) -> None:
        @builder.run_and_check_after
        def _() -> None:
            builder.set_and_copy_installed_apps("leader", "follower1")
            builder.on("main.py").set(
                """
                from follower1 import models as f1models
                from django.db import models
                from typing import TypedDict, Any
                from extended_mypy_django_plugin import hide_queryset_annotations
                from django_stubs_ext import WithAnnotations

                class _Annotation(TypedDict):
                    value: Any

                type FollowerWithAnnotation = WithAnnotations[f1models.Follower1, _Annotation]

                def without_helper(qs: models.QuerySet[FollowerWithAnnotation]) -> models.QuerySet[f1models.Follower1]:
                    without_annotation = hide_queryset_annotations(qs)
                    # ^ REVEAL ^ django.db.models.query.QuerySet[follower1.models.follower1.Follower1]

                    return qs
                    # it seems django-stubs already is fine with this
                """
            )

    def test_works_in_custom_queryset_methods(self, builder: ScenarioBuilder) -> None:
        @builder.run_and_check_after
        def _() -> None:
            builder.set_installed_apps("example")
            builder.on("example/__init__.py").set("")

            builder.on("example/apps.py").set(
                """
                from django.apps import AppConfig

                class Config(AppConfig):
                    name = "example"
                """,
            )

            builder.on("example/models.py").set(
                """
                from __future__ import annotations

                from django.db import models
                from extended_mypy_django_plugin import hide_queryset_annotations
                from typing import Self

                class MyModelQuerySet[T_Model: MyModel = MyModel](models.QuerySet[T_Model]):
                    def without_helper(self) -> Self:
                        return self.annotate(value=models.Value(1)).filter(value=1)
                        # Seems django-stubs already doesn't realise this is annotated

                    def with_helper(self) -> Self:
                        qs = self.annotate(value=models.Value(1)).filter(value=1)
                        # ^ REVEAL ^ Self

                        without_annotations = hide_queryset_annotations(qs)
                        # ^ REVEAL ^ Self

                        return without_annotations

                class MyModel(models.Model):
                    objects = MyModelQuerySet.as_manager()
                """,
            )

            builder.on("main.py").set(
                """
                from example.models import MyModel

                one = MyModel.objects.all().without_helper()
                # ^ REVEAL[model] ^ example.models.MyModelQuerySet[example.models.MyModel]

                two = MyModel.objects.all().with_helper()
                # ^ REVEAL[model] ^ example.models.MyModelQuerySet[example.models.MyModel]
                """,
            )

    def test_it_complains_when_passing_in_things_that_are_not_queryset_instances(
        self, builder: ScenarioBuilder
    ) -> None:
        @builder.run_and_check_after
        def _() -> None:
            builder.set_and_copy_installed_apps("leader", "follower1")
            builder.on("main.py").set(
                """
                from follower1 import models as f1models
                from extended_mypy_django_plugin import hide_queryset_annotations
                from typing import Self, Any
                from django.db import models

                hide_queryset_annotations(1)
                # ^ ERROR(misc) ^ Failed to determine a django model from the first argument (or it's not a queryset)
                
                hide_queryset_annotations("asdf")
                # ^ ERROR(misc) ^ Failed to determine a django model from the first argument (or it's not a queryset)

                hide_queryset_annotations(f1models.Follower1)
                # ^ ERROR(misc) ^ First argument must be an instance

                hide_queryset_annotations(f1models.Follower1QuerySet)
                # ^ ERROR(misc) ^ First argument must be an instance

                class MyClass:
                    def my_method(self) -> Self:
                        return hide_queryset_annotations(self)
                        # ^ ERROR(misc) ^ First argument must be a queryset

                def do_not_know_type(arg: Any) -> None:
                    hide_queryset_annotations(arg)
                    # ^ ERROR(misc) ^ Failed to determine the type of the first argument
                    
                def do_not_know_model(arg: models.QuerySet[Any]) -> None:
                    hide_queryset_annotations(arg)
                    # ^ ERROR(misc) ^ Failed to determine a django model from the first argument (or it's not a queryset)
                """
            )

    def test_can_access_helper_from_a_different_location(self, builder: ScenarioBuilder) -> None:
        @builder.run_and_check_after
        def _() -> None:
            builder.set_and_copy_installed_apps("leader", "follower1")
            builder.on("type_inference.py").set(
                """
                from extended_mypy_django_plugin import hide_queryset_annotations

                hide_queryset_annotations = hide_queryset_annotations
                """
            )
            builder.on("main.py").set(
                """
                from django.db import models
                import type_inference
                from follower1 import models as f1models

                qs = f1models.Follower1.objects.all().annotate(value=models.Value(1)).filter(value=1)
                # ^ REVEAL ^ follower1.models.follower1.Follower1QuerySet[follower1.models.follower1.Follower1@AnnotatedWith[TypedDict({'value': Any})], follower1.models.follower1.Follower1@AnnotatedWith[TypedDict({'value': Any})]]

                without_annotations = type_inference.hide_queryset_annotations(qs)
                # ^ REVEAL ^ follower1.models.follower1.Follower1QuerySet[follower1.models.follower1.Follower1]
                """
            )
