from extended_mypy_django_plugin_test_driver import OutputBuilder, Scenario


class TestConcreteAnnotations:
    def test_simple_annotation(self, scenario: Scenario) -> None:
        @scenario.run_and_check_mypy_after
        def _(expected: OutputBuilder) -> None:
            scenario.make_file_with_reveals(
                expected,
                19,
                "main.py",
                """
                from extended_mypy_django_plugin import Concrete, DefaultQuerySet
                from typing import cast, TypeGuard

                from myapp.models import Parent, Child1, Child2

                def check_cls_with_type_guard(cls: type[Parent]) -> TypeGuard[type[Concrete[Parent]]]:
                    return True

                def check_instance_with_type_guard(cls: Parent) -> TypeGuard[Concrete[Parent]]:
                    return True

                models: Concrete[Parent]
                # ^ REVEAL models ^ Union[myapp.models.Child1, myapp.models.Child2, myapp.models.Child3, myapp2.models.ChildOther]

                qs: DefaultQuerySet[Parent]
                # ^ REVEAL qs ^ Union[django.db.models.query.QuerySet[myapp.models.Child1, myapp.models.Child1], myapp.models.Child2QuerySet, django.db.models.query.QuerySet[myapp.models.Child3, myapp.models.Child3], django.db.models.query.QuerySet[myapp2.models.ChildOther, myapp2.models.ChildOther]]

                cls: type[Parent] = Child1
                assert check_cls_with_type_guard(cls)
                # ^ REVEAL cls ^ Union[type[myapp.models.Child1], type[myapp.models.Child2], type[myapp.models.Child3], type[myapp2.models.ChildOther]]

                instance: Parent = cast(Child1, None)
                assert check_instance_with_type_guard(instance)
                # ^ REVEAL instance ^ Union[myapp.models.Child1, myapp.models.Child2, myapp.models.Child3, myapp2.models.ChildOther]

                children: Concrete[Parent]
                # ^ REVEAL children ^ Union[myapp.models.Child1, myapp.models.Child2, myapp.models.Child3, myapp2.models.ChildOther]

                children_qs: DefaultQuerySet[Parent]
                # ^ REVEAL children_qs ^ Union[django.db.models.query.QuerySet[myapp.models.Child1, myapp.models.Child1], myapp.models.Child2QuerySet, django.db.models.query.QuerySet[myapp.models.Child3, myapp.models.Child3], django.db.models.query.QuerySet[myapp2.models.ChildOther, myapp2.models.ChildOther]]

                child: Concrete[Child1]
                # ^ REVEAL child ^ myapp.models.Child1

                child1_qs: DefaultQuerySet[Child1]
                # ^ REVEAL child1_qs ^ django.db.models.query.QuerySet[myapp.models.Child1, myapp.models.Child1]

                child2_qs: DefaultQuerySet[Child2]
                # ^ REVEAL child2_qs ^ myapp.models.Child2QuerySet

                t1_children: type[Concrete[Parent]]
                # ^ REVEAL t1_children ^ Union[type[myapp.models.Child1], type[myapp.models.Child2], type[myapp.models.Child3], type[myapp2.models.ChildOther]]

                t1_children_qs: type[DefaultQuerySet[Parent]]
                # ^ REVEAL t1_children_qs ^ Union[type[django.db.models.query.QuerySet[myapp.models.Child1, myapp.models.Child1]], type[myapp.models.Child2QuerySet], type[django.db.models.query.QuerySet[myapp.models.Child3, myapp.models.Child3]], type[django.db.models.query.QuerySet[myapp2.models.ChildOther, myapp2.models.ChildOther]]]

                t1_child: type[Concrete[Child1]]
                # ^ REVEAL t1_child ^ type[myapp.models.Child1]

                t1_child1_qs: type[DefaultQuerySet[Child1]]
                # ^ REVEAL t1_child1_qs ^ type[django.db.models.query.QuerySet[myapp.models.Child1, myapp.models.Child1]]

                t1_child2_qs: type[DefaultQuerySet[Child2]]
                # ^ REVEAL t1_child2_qs ^ type[myapp.models.Child2QuerySet]

                t2_children: Concrete[type[Parent]]
                # ^ REVEAL t2_children ^ Union[type[myapp.models.Child1], type[myapp.models.Child2], type[myapp.models.Child3], type[myapp2.models.ChildOther]]

                t2_children_qs: DefaultQuerySet[type[Parent]]
                # ^ REVEAL t2_children_qs ^ Union[type[django.db.models.query.QuerySet[myapp.models.Child1, myapp.models.Child1]], type[myapp.models.Child2QuerySet], type[django.db.models.query.QuerySet[myapp.models.Child3, myapp.models.Child3]], type[django.db.models.query.QuerySet[myapp2.models.ChildOther, myapp2.models.ChildOther]]]

                t2_child: Concrete[type[Child1]]
                # ^ REVEAL t2_child ^ type[myapp.models.Child1]

                t2_child1_qs: DefaultQuerySet[type[Child1]]
                # ^ REVEAL t2_child1_qs ^ type[django.db.models.query.QuerySet[myapp.models.Child1, myapp.models.Child1]]

                t2_child2_qs: DefaultQuerySet[type[Child2]]
                # ^ REVEAL t2_child2_qs ^ type[myapp.models.Child2QuerySet]
                """,
            )

    def test_using_concrete_annotation_on_class_used_in_annotation(
        self, scenario: Scenario
    ) -> None:
        @scenario.run_and_check_mypy_after(installed_apps=["example"])
        def _(expected: OutputBuilder) -> None:
            scenario.make_file("example/__init__.py", "")

            scenario.make_file(
                "example/apps.py",
                """
                from django.apps import AppConfig

                class Config(AppConfig):
                    name = "example"
                """,
            )

            scenario.make_file(
                "example/models.py",
                """
                from __future__ import annotations

                from django.db import models
                from typing_extensions import Self
                from extended_mypy_django_plugin import Concrete, DefaultQuerySet

                class Leader(models.Model):
                    @classmethod
                    def new(cls) -> Concrete[Self]:
                        cls = Concrete.cast_as_concrete(cls)
                        # ^ REVEAL cls ^ Union[type[example.models.Follower1], type[example.models.Follower2]]
                        return cls.objects.create()

                    def qs(self) -> DefaultQuerySet[Self]:
                        self = Concrete.cast_as_concrete(self)
                        # ^ REVEAL self ^ Union[example.models.Follower1, example.models.Follower2]
                        return self.__class__.objects.filter(pk=self.pk)

                    class Meta:
                        abstract = True

                T_Leader = Concrete.type_var("T_Leader", Leader)

                class Follower1QuerySet(models.QuerySet["Follower1"]):
                    ...

                Follower1Manager = models.Manager.from_queryset(Follower1QuerySet)

                class Follower1(Leader):
                    objects = Follower1Manager()

                class Follower2(Leader):
                    ...

                def make_queryset(cls: T_Leader) -> DefaultQuerySet[T_Leader]:
                    return cls.qs()
                """,
            )

            scenario.make_file_with_reveals(
                expected,
                9,
                "main.py",
                """
                from example.models import Leader, Follower1, Follower2, make_queryset
                from extended_mypy_django_plugin import Concrete

                model: type[Leader] = Follower1
                # ^ REVEAL model ^ type[example.models.Leader]

                leader = model.new()
                # ^ REVEAL leader ^ Union[example.models.Follower1, example.models.Follower2]

                qs = leader.qs()
                # ^ REVEAL qs ^ Union[example.models.Follower1QuerySet, django.db.models.query.QuerySet[example.models.Follower2, example.models.Follower2]]

                follower1 = Follower1.new()
                # ^ REVEAL follower1 ^ example.models.Follower1

                qs2 = make_queryset(follower1)
                # ^ REVEAL qs2 ^ example.models.Follower1QuerySet

                qs3 = Follower2.new().qs()
                # ^ REVEAL qs3 ^ django.db.models.query.QuerySet[example.models.Follower2, example.models.Follower2]

                other: Leader = Follower1.new()
                # ^ REVEAL other ^ example.models.Leader

                narrowed = Concrete.cast_as_concrete(other)
                # ^ REVEAL narrowed ^ Union[example.models.Follower1, example.models.Follower2]
                # ^ REVEAL other ^ example.models.Leader
                """,
            )

            # Fixed in a future commit
            (
                expected.on("example/models.py").add_error(
                    22, "misc", "No concrete children found for example.models.Leader"
                )
            )

    def test_sees_apps_removed_when_they_still_exist_but_no_longer_installed(
        self, scenario: Scenario
    ) -> None:
        @scenario.run_and_check_mypy_after
        def _(expected: OutputBuilder) -> None:
            scenario.make_file(
                "main.py",
                """
                from extended_mypy_django_plugin import Concrete, DefaultQuerySet

                from myapp.models import Parent

                models: Concrete[Parent]
                reveal_type(models)

                qs: DefaultQuerySet[Parent]
                reveal_type(qs)
                """,
            )

            (
                expected.on("main.py")
                .add_revealed_type(
                    6,
                    "Union[myapp.models.Child1, myapp.models.Child2, myapp.models.Child3, myapp2.models.ChildOther]",
                )
                .add_revealed_type(
                    9,
                    "Union[django.db.models.query.QuerySet[myapp.models.Child1, myapp.models.Child1], myapp.models.Child2QuerySet, django.db.models.query.QuerySet[myapp.models.Child3, myapp.models.Child3], django.db.models.query.QuerySet[myapp2.models.ChildOther, myapp2.models.ChildOther]]",
                )
            )

        # Now let's remove myapp2 from the installed_apps and see that the daemon restarts and myapp2 is removed from the revealed types

        @scenario.run_and_check_mypy_after(installed_apps=["myapp"])
        def _(expected: OutputBuilder) -> None:
            expected.daemon_should_restart()

            (
                expected.on("main.py")
                .remove_from_revealed_type(
                    6,
                    ", myapp2.models.ChildOther",
                )
                .remove_from_revealed_type(
                    9,
                    ", django.db.models.query.QuerySet[myapp2.models.ChildOther, myapp2.models.ChildOther]",
                )
            )

    def test_does_not_see_apps_that_exist_but_are_not_installed(self, scenario: Scenario) -> None:
        @scenario.run_and_check_mypy_after(
            installed_apps=["myapp"], copied_apps=["myapp", "myapp2"]
        )
        def _(expected: OutputBuilder) -> None:
            scenario.make_file(
                "main.py",
                """
                from extended_mypy_django_plugin import Concrete, DefaultQuerySet

                from myapp.models import Parent

                model: Concrete[Parent]
                model.concrete_from_myapp

                qs: DefaultQuerySet[Parent]
                qs.values("concrete_from_myapp")
                """,
            )

        # And after installing the app means the types expand

        @scenario.run_and_check_mypy_after(installed_apps=["myapp", "myapp2"])
        def _(expected: OutputBuilder) -> None:
            expected.daemon_should_restart()

            (
                expected.on("main.py")
                .add_error(
                    6,
                    "union-attr",
                    'Item "ChildOther" of "Child1 | Child2 | Child3 | ChildOther" has no attribute "concrete_from_myapp"',
                )
                .add_error(
                    9,
                    "misc",
                    "Cannot resolve keyword 'concrete_from_myapp' into field. Choices are: concrete_from_myapp2, id, one, two",
                )
            )

    def test_sees_models_when_they_are_added_and_installed(self, scenario: Scenario) -> None:
        @scenario.run_and_check_mypy_after(installed_apps=["myapp"])
        def _(expected: OutputBuilder) -> None:
            scenario.make_file(
                "main.py",
                """
                from extended_mypy_django_plugin import Concrete, DefaultQuerySet

                from myapp.models import Parent

                models: Concrete[Parent]
                reveal_type(models)

                qs: DefaultQuerySet[Parent]
                qs.values("concrete_from_myapp")
                """,
            )

            (
                expected.on("main.py").add_revealed_type(
                    6, "Union[myapp.models.Child1, myapp.models.Child2, myapp.models.Child3]"
                )
            )

        # and the models become available after being installed

        @scenario.run_and_check_mypy_after(installed_apps=["myapp", "myapp2"])
        def _(expected: OutputBuilder) -> None:
            expected.daemon_should_restart()

            (
                expected.on("main.py")
                .change_revealed_type(
                    6,
                    "Union[myapp.models.Child1, myapp.models.Child2, myapp.models.Child3, myapp2.models.ChildOther]",
                )
                .add_error(
                    9,
                    "misc",
                    "Cannot resolve keyword 'concrete_from_myapp' into field. Choices are: concrete_from_myapp2, id, one, two",
                )
            )

        # And same output if nothing changes

        @scenario.run_and_check_mypy_after
        def _(expected: OutputBuilder) -> None:
            expected.daemon_should_not_restart()

    def test_sees_new_models(self, scenario: Scenario) -> None:
        @scenario.run_and_check_mypy_after
        def _(expected: OutputBuilder) -> None:
            scenario.make_file(
                "main.py",
                """
                from extended_mypy_django_plugin import Concrete, DefaultQuerySet

                from myapp.models import Parent

                models: Concrete[Parent]
                models.two

                qs: DefaultQuerySet[Parent]
                qs.values("two")
                """,
            )

        # And if we add some more models

        @scenario.run_and_check_mypy_after
        def _(expected: OutputBuilder) -> None:
            scenario.append_to_file(
                "myapp2/models.py",
                """
                class Another(Parent):
                    pass
                """,
            )

            expected.daemon_should_restart()

            (
                expected.on("main.py")
                .add_error(
                    6,
                    "union-attr",
                    'Item "Another" of "Child1 | Child2 | Child3 | Another | ChildOther" has no attribute "two"',
                )
                .add_error(
                    9, "misc", "Cannot resolve keyword 'two' into field. Choices are: id, one"
                )
            )

        # And the new model remains after a rerun

        @scenario.run_and_check_mypy_after
        def _(expected: OutputBuilder) -> None:
            expected.daemon_should_not_restart()

    def test_sees_changes_in_custom_querysets_within_app(self, scenario: Scenario) -> None:
        @scenario.run_and_check_mypy_after(installed_apps=["leader", "follower1"])
        def _(expected: OutputBuilder) -> None:
            scenario.make_file(
                "main.py",
                """
                from extended_mypy_django_plugin import Concrete, DefaultQuerySet

                from leader.models import Leader

                models: Concrete[Leader]
                reveal_type(models)

                qs: DefaultQuerySet[Leader]
                reveal_type(qs)
                qs.good_ones().values("nup")
                """,
            )

            (
                expected.on("main.py")
                .add_revealed_type(6, "follower1.models.follower1.Follower1")
                .add_revealed_type(9, "follower1.models.follower1.Follower1QuerySet")
                .add_error(
                    10,
                    "misc",
                    "Cannot resolve keyword 'nup' into field. Choices are: from_follower1, good, id",
                )
            )

        # And then add another model

        @scenario.run_and_check_mypy_after
        def _(expected: OutputBuilder) -> None:
            scenario.update_file(
                "follower1/models/__init__.py",
                """
                from .follower1 import Follower1
                from .follower2 import Follower2

                __all__ = ["Follower1", "Follower2"]
                """,
            )

            scenario.update_file(
                "follower1/models/follower2.py",
                """
                from django.db import models
                from leader.models import Leader

                class Follower2QuerySet(models.QuerySet["Follower2"]):
                    def good_ones(self) -> "Follower2QuerySet":
                        return self.filter(good=True)

                Follower2Manager = models.Manager.from_queryset(Follower2QuerySet)

                class Follower2(Leader):
                    good = models.BooleanField()

                    objects = Follower2Manager()
                """,
            )

            expected.clear()

            expected.daemon_should_restart()

            (
                expected.on("main.py")
                .add_revealed_type(
                    6,
                    "Union[follower1.models.follower1.Follower1, follower1.models.follower2.Follower2]",
                )
                .add_revealed_type(
                    9,
                    "Union[follower1.models.follower1.Follower1QuerySet, follower1.models.follower2.Follower2QuerySet]",
                )
                .add_error(
                    10,
                    "misc",
                    "Cannot resolve keyword 'nup' into field. Choices are: from_follower1, good, id",
                )
                .add_error(
                    10, "misc", "Cannot resolve keyword 'nup' into field. Choices are: good, id"
                )
            )

        # And same output, no daemon restart on no change

        @scenario.run_and_check_mypy_after
        def _(expected: OutputBuilder) -> None:
            expected.daemon_should_not_restart()

        # And removing the method from the queryset

        @scenario.run_and_check_mypy_after
        def _(expected: OutputBuilder) -> None:
            scenario.update_file(
                "follower1/models/follower2.py",
                """
                from django.db import models
                from leader.models import Leader

                class Follower2QuerySet(models.QuerySet["Follower2"]):
                    pass

                Follower2Manager = models.Manager.from_queryset(Follower2QuerySet)

                class Follower2(Leader):
                    good = models.BooleanField()

                    objects = Follower2Manager()
                """,
            )

            (
                expected.on("main.py")
                .remove_errors(10)
                .add_error(
                    10,
                    "union-attr",
                    'Item "Follower2QuerySet" of "Follower1QuerySet | Follower2QuerySet" has no attribute "good_ones"',
                )
                .add_error(
                    10,
                    "misc",
                    "Cannot resolve keyword 'nup' into field. Choices are: from_follower1, good, id",
                )
            )

    def test_sees_changes_in_custom_querysets_in_new_apps(self, scenario: Scenario) -> None:
        @scenario.run_and_check_mypy_after(installed_apps=["leader", "follower1"])
        def _(expected: OutputBuilder) -> None:
            scenario.make_file(
                "main.py",
                """
                from extended_mypy_django_plugin import Concrete, DefaultQuerySet

                from leader.models import Leader

                models: Concrete[Leader]
                reveal_type(models)

                qs: DefaultQuerySet[Leader]
                reveal_type(qs)
                qs.good_ones().values("nup")
                """,
            )

            (
                expected.on("main.py")
                .add_revealed_type(6, "follower1.models.follower1.Follower1")
                .add_revealed_type(9, "follower1.models.follower1.Follower1QuerySet")
                .add_error(
                    10,
                    "misc",
                    "Cannot resolve keyword 'nup' into field. Choices are: from_follower1, good, id",
                )
            )

        # Let's then add a new app with new models

        @scenario.run_and_check_mypy_after(installed_apps=["leader", "follower1", "follower2"])
        def _(expected: OutputBuilder) -> None:
            scenario.update_file("follower2/__init__.py", "")

            scenario.update_file(
                "follower2/apps.py",
                """
                from django.apps import AppConfig
                class Config(AppConfig):
                    default_auto_field = "django.db.models.BigAutoField"
                    name = "follower2"
                """,
            )

            scenario.update_file(
                "follower2/models.py",
                """
                from django.db import models
                from leader.models import Leader

                class Follower2QuerySet(models.QuerySet["Follower2"]):
                    def good_ones(self) -> "Follower2QuerySet":
                        return self.filter(good=True)

                Follower2Manager = models.Manager.from_queryset(Follower2QuerySet)

                class Follower2(Leader):
                    good = models.BooleanField()

                    objects = Follower2Manager()
                """,
            )

            expected.daemon_should_restart()

            (
                expected.on("main.py")
                .change_revealed_type(
                    6, "Union[follower1.models.follower1.Follower1, follower2.models.Follower2]"
                )
                .change_revealed_type(
                    9,
                    "Union[follower1.models.follower1.Follower1QuerySet, follower2.models.Follower2QuerySet]",
                )
                .add_error(
                    10, "misc", "Cannot resolve keyword 'nup' into field. Choices are: good, id"
                )
            )

        # And everything stays the same on rerun

        @scenario.run_and_check_mypy_after
        def _(expected: OutputBuilder) -> None:
            expected.daemon_should_not_restart()

        # And it sees where custom queryset gets queryset manager removed

        @scenario.run_and_check_mypy_after
        def _(expected: OutputBuilder) -> None:
            scenario.update_file(
                "follower2/models.py",
                """
                from django.db import models
                from leader.models import Leader

                class Follower2QuerySet(models.QuerySet["Follower2"]):
                    pass

                Follower2Manager = models.Manager.from_queryset(Follower2QuerySet)

                class Follower2(Leader):
                    good = models.BooleanField()

                    objects = Follower2Manager()
                """,
            )

            (
                expected.on("main.py")
                .remove_errors(10)
                .add_error(
                    10,
                    "union-attr",
                    'Item "Follower2QuerySet" of "Follower1QuerySet | Follower2QuerySet" has no attribute "good_ones"',
                )
                .add_error(
                    10,
                    "misc",
                    "Cannot resolve keyword 'nup' into field. Choices are: from_follower1, good, id",
                )
            )
