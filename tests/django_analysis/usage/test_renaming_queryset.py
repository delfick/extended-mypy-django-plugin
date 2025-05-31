import pathlib
import textwrap

from extended_mypy_django_plugin_test_driver import ScenarioBuilder


class TestRenamingQuerySet:
    def test_can_move_queryset_from_abstract_class_to_concrete_children(
        self, builder: ScenarioBuilder, tmp_path: pathlib.Path
    ) -> None:
        builder.set_installed_apps("parent", "child1", "child2")
        for app in ("parent", "child1", "child2"):
            builder.on(f"{app}/__init__.py").set("")
            builder.on(f"{app}/apps.py").set(
                f"""
                from django.apps import AppConfig

                class Config(AppConfig):
                    name = "{app}"
                """,
            )

        builder.on("parent/models.py").set(
            """
            from typing import TYPE_CHECKING, Union
            from django.db import models


            if TYPE_CHECKING:
                from child1.models import Child1
                from child2.models import Child2

            class ParentQuerySet(models.QuerySet[Union["Child1", "Child2"]]):
                pass

            ParentManager = models.Manager.from_queryset(ParentQuerySet)


            class Parent(models.Model):
                objects = ParentManager()

                class Meta:
                    abstract = True
            """
        )
        builder.on("child1/models.py").set(
            """
            from parent.models import Parent

            class Child1(Parent):
                pass
            """
        )
        builder.on("child2/models.py").set(
            """
            from parent.models import Parent

            class Child2(Parent):
                pass
            """
        )

        deps_dest = tmp_path / ".mypy_django_deps"

        builder.populate_virtual_deps(deps_dest=deps_dest)

        expected = {
            "mod_3961720227.py": """
                def interface__timestamp() -> None:
                    return None

                mod = "django.contrib.contenttypes.models"
                summary = "__virtual_extended_mypy_django_plugin_report__.mod_3961720227::django.contrib.contenttypes.models::installed_apps=3376484868::significant=438215680::v2"

                import django.contrib.contenttypes.models
                import django.db.models
                ConcreteQuerySet__ContentType = django.db.models.QuerySet[django.contrib.contenttypes.models.ContentType]
                Concrete__ContentType = django.contrib.contenttypes.models.ContentType
                """,
            "mod_566232296.py": """
                def interface__timestamp() -> None:
                    return None

                mod = "child1.models"
                summary = "__virtual_extended_mypy_django_plugin_report__.mod_566232296::child1.models::installed_apps=3376484868::significant=967422822::v2"

                import child1.models
                import parent.models
                ConcreteQuerySet__Child1 = parent.models.ParentQuerySet
                Concrete__Child1 = child1.models.Child1
                """,
            "mod_566756585.py": """
                def interface__timestamp() -> None:
                    return None

                mod = "child2.models"
                summary = "__virtual_extended_mypy_django_plugin_report__.mod_566756585::child2.models::installed_apps=3376484868::significant=1344320379::v2"

                import child2.models
                import parent.models
                ConcreteQuerySet__Child2 = parent.models.ParentQuerySet
                Concrete__Child2 = child2.models.Child2
                """,
            "mod_614729021.py": """
                def interface__timestamp() -> None:
                    return None

                mod = "parent.models"
                summary = "__virtual_extended_mypy_django_plugin_report__.mod_614729021::parent.models::installed_apps=3376484868::significant=309881802::v2"

                import child1.models
                import child2.models
                import parent.models
                ConcreteQuerySet__Parent = parent.models.ParentQuerySet
                Concrete__Parent = child1.models.Child1 | child2.models.Child2
                """,
        }

        for fle in (deps_dest / "__virtual_extended_mypy_django_plugin_report__").iterdir():
            want = textwrap.dedent(expected[fle.name]).strip()
            assert fle.read_text().strip() == want

        builder.on("parent/models.py").set(
            """
            from typing import TYPE_CHECKING, Union, TypeVar
            from extended_mypy_django_plugin import Concrete
            from django.db import models

            T_Child = TypeVar("T_Child", bound=Concrete["Parent"])

            class ParentQuerySet(models.QuerySet[T_Child]):
                pass


            class Parent(models.Model):
                class Meta:
                    abstract = True
            """
        )
        builder.on("child1/models.py").set(
            """
            from parent.models import Parent, ParentQuerySet
            from django.db import models

            class Child1QuerySet(ParentQuerySet["Child1"]):
                pass

            Child1Manager = models.Manager.from_queryset(Child1QuerySet)

            class Child1(Parent):
                objects = Child1Manager()
            """
        )
        builder.on("child2/models.py").set(
            """
            from parent.models import Parent, ParentQuerySet
            from django.db import models

            class Child2QuerySet(ParentQuerySet["Child1"]):
                pass

            Child2Manager = models.Manager.from_queryset(Child2QuerySet)


            class Child2(Parent):
                objects = Child2Manager()
            """
        )

        expected["mod_566232296.py"] = """
            def interface__timestamp() -> None:
                return None

            mod = "child1.models"
            summary = "__virtual_extended_mypy_django_plugin_report__.mod_566232296::child1.models::installed_apps=3376484868::significant=2468262588::v2"

            import child1.models
            ConcreteQuerySet__Child1 = child1.models.Child1QuerySet
            Concrete__Child1 = child1.models.Child1
            """

        expected["mod_566756585.py"] = """
            def interface__timestamp() -> None:
                return None

            mod = "child2.models"
            summary = "__virtual_extended_mypy_django_plugin_report__.mod_566756585::child2.models::installed_apps=3376484868::significant=2877928147::v2"

            import child2.models
            ConcreteQuerySet__Child2 = child2.models.Child2QuerySet
            Concrete__Child2 = child2.models.Child2
            """

        expected["mod_614729021.py"] = """
            def interface__timestamp() -> None:
                return None

            mod = "parent.models"
            summary = "__virtual_extended_mypy_django_plugin_report__.mod_614729021::parent.models::installed_apps=3376484868::significant=3300935593::v2"

            import child1.models
            import child2.models
            import parent.models
            ConcreteQuerySet__Parent = child1.models.Child1QuerySet | child2.models.Child2QuerySet
            Concrete__Parent = child1.models.Child1 | child2.models.Child2
            """

        builder.populate_virtual_deps(deps_dest=deps_dest)

        for fle in sorted(
            (deps_dest / "__virtual_extended_mypy_django_plugin_report__").iterdir()
        ):
            want = textwrap.dedent(expected[fle.name]).strip()
            assert fle.read_text().strip() == want

    def test_can_rename_duplicate_concrete_querysets(
        self, builder: ScenarioBuilder, tmp_path: pathlib.Path
    ) -> None:
        builder.set_installed_apps("parent", "child1", "child2")
        for app in ("parent", "child1", "child2"):
            builder.on(f"{app}/__init__.py").set("")
            builder.on(f"{app}/apps.py").set(
                f"""
                from django.apps import AppConfig

                class Config(AppConfig):
                    name = "{app}"
                """,
            )

        builder.on("parent/models.py").set(
            """
            from typing import TYPE_CHECKING, Union
            from django.db import models


            if TYPE_CHECKING:
                from child1.models import Child1
                from child2.models import Child2

            class Parent(models.Model):
                class Meta:
                    abstract = True
            """
        )
        builder.on("child1/models.py").set(
            """
            from parent.models import Parent
            from django.db import models

            class ChildQuerySet(models.QuerySet["Child"]):
                pass

            ChildManager = models.Manager.from_queryset(ChildQuerySet)

            class Child(Parent):
                objects = ChildManager()
            """
        )
        builder.on("child2/models.py").set(
            """
            from parent.models import Parent
            from django.db import models

            class ChildQuerySet(models.QuerySet["Child"]):
                pass

            ChildManager = models.Manager.from_queryset(ChildQuerySet)

            class Child(Parent):
                objects = ChildManager()
            """
        )

        deps_dest = tmp_path / ".mypy_django_deps"

        pathlib.Path("/tmp/debug").unlink(missing_ok=True)
        builder.populate_virtual_deps(deps_dest=deps_dest)

        expected = {
            "mod_3961720227.py": """
                def interface__timestamp() -> None:
                    return None

                mod = "django.contrib.contenttypes.models"
                summary = "__virtual_extended_mypy_django_plugin_report__.mod_3961720227::django.contrib.contenttypes.models::installed_apps=3376484868::significant=438215680::v2"

                import django.contrib.contenttypes.models
                import django.db.models
                ConcreteQuerySet__ContentType = django.db.models.QuerySet[django.contrib.contenttypes.models.ContentType]
                Concrete__ContentType = django.contrib.contenttypes.models.ContentType
                """,
            "mod_566232296.py": """
                def interface__timestamp() -> None:
                    return None

                mod = "child1.models"
                summary = "__virtual_extended_mypy_django_plugin_report__.mod_566232296::child1.models::installed_apps=3376484868::significant=1784590644::v2"

                import child1.models
                ConcreteQuerySet__Child = child1.models.ChildQuerySet
                Concrete__Child = child1.models.Child
                """,
            "mod_566756585.py": """
                def interface__timestamp() -> None:
                    return None

                mod = "child2.models"
                summary = "__virtual_extended_mypy_django_plugin_report__.mod_566756585::child2.models::installed_apps=3376484868::significant=2056565059::v2"

                import child2.models
                ConcreteQuerySet__Child = child2.models.ChildQuerySet
                Concrete__Child = child2.models.Child
                """,
            "mod_614729021.py": """
                def interface__timestamp() -> None:
                    return None

                mod = "parent.models"
                summary = "__virtual_extended_mypy_django_plugin_report__.mod_614729021::parent.models::installed_apps=3376484868::significant=1191855927::v2"

                import child1.models
                import child2.models
                import parent.models
                ConcreteQuerySet__Parent = child1.models.ChildQuerySet | child2.models.ChildQuerySet
                Concrete__Parent = child1.models.Child | child2.models.Child
                """,
        }

        for fle in (deps_dest / "__virtual_extended_mypy_django_plugin_report__").iterdir():
            want = textwrap.dedent(expected[fle.name]).strip()
            assert fle.read_text().strip() == want

        builder.on("child1/models.py").set(
            """
            from parent.models import Parent
            from django.db import models

            class _Child1QuerySet(models.QuerySet["Child"]):
                pass

            ChildQuerySet = _Child1QuerySet
            ChildManager = models.Manager.from_queryset(_Child1QuerySet)

            class Child(Parent):
                objects = ChildManager()
            """
        )
        builder.on("child2/models.py").set(
            """
            from parent.models import Parent
            from django.db import models

            class _Child2QuerySet(models.QuerySet["Child"]):
                pass

            ChildQuerySet = _Child2QuerySet
            ChildManager = models.Manager.from_queryset(_Child2QuerySet)

            class Child(Parent):
                objects = ChildManager()
            """
        )

        expected["mod_566232296.py"] = """
            def interface__timestamp() -> None:
                return None

            mod = "child1.models"
            summary = "__virtual_extended_mypy_django_plugin_report__.mod_566232296::child1.models::installed_apps=3376484868::significant=2733879748::v2"

            import child1.models
            ConcreteQuerySet__Child = child1.models._Child1QuerySet
            Concrete__Child = child1.models.Child
            """

        expected["mod_566756585.py"] = """
            def interface__timestamp() -> None:
                return None

            mod = "child2.models"
            summary = "__virtual_extended_mypy_django_plugin_report__.mod_566756585::child2.models::installed_apps=3376484868::significant=3022762452::v2"

            import child2.models
            ConcreteQuerySet__Child = child2.models._Child2QuerySet
            Concrete__Child = child2.models.Child
            """

        expected["mod_614729021.py"] = """
            def interface__timestamp() -> None:
                return None

            mod = "parent.models"
            summary = "__virtual_extended_mypy_django_plugin_report__.mod_614729021::parent.models::installed_apps=3376484868::significant=1197557559::v2"

            import child1.models
            import child2.models
            import parent.models
            ConcreteQuerySet__Parent = child1.models._Child1QuerySet | child2.models._Child2QuerySet
            Concrete__Parent = child1.models.Child | child2.models.Child
            """

        pathlib.Path("/tmp/debug").write_text("")
        builder.populate_virtual_deps(deps_dest=deps_dest)

        for fle in sorted(
            (deps_dest / "__virtual_extended_mypy_django_plugin_report__").iterdir()
        ):
            want = textwrap.dedent(expected[fle.name]).strip()
            assert fle.read_text().strip() == want
