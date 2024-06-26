import functools
import importlib
import pathlib
import shutil
import textwrap

import pytest

from extended_mypy_django_plugin.django_analysis import (
    ImportPath,
    Project,
    adler32_hash,
    protocols,
    virtual_dependencies,
)

ReportSummaryGetter = virtual_dependencies.ReportSummaryGetter


class TestVirtualDependencyScribe:
    class TestGetSummary:
        @pytest.fixture
        def get_report_summary(self) -> ReportSummaryGetter:
            return virtual_dependencies.VirtualDependencyScribe.get_report_summary

        def test_it_says_no_to_directories(
            self, tmp_path: pathlib.Path, get_report_summary: ReportSummaryGetter
        ) -> None:
            assert get_report_summary(tmp_path) is None

        def test_it_says_no_if_the_path_doesnt_end_in_python_extension(
            self, tmp_path: pathlib.Path, get_report_summary: ReportSummaryGetter
        ) -> None:
            (without_extension := tmp_path / "one").write_text(
                'mod = "extended_mypy_django_plugin.version"\nsummary = "stuff"'
            )

            assert get_report_summary(without_extension) is None

            with_extension = tmp_path / "one.py"
            shutil.move(without_extension, with_extension)

            assert get_report_summary(with_extension) == "stuff"

        def test_it_says_yes_to_files_and_links(
            self, tmp_path: pathlib.Path, get_report_summary: ReportSummaryGetter
        ) -> None:
            (one := tmp_path / "one.py").write_text(
                'mod = "extended_mypy_django_plugin.version"\nsummary = "trees"'
            )
            (two := tmp_path / "two.py").symlink_to(one)

            assert get_report_summary(one) == "trees"
            assert get_report_summary(two) == "trees"

        def test_it_says_no_if_cant_find_mod(
            self, tmp_path: pathlib.Path, get_report_summary: ReportSummaryGetter
        ) -> None:
            (location := tmp_path / "one.py").write_text('summary = "things"')
            assert get_report_summary(location) is None

            with open(location, "a") as fle:
                fle.write('\nmod = "extended_mypy_django_plugin.version"')

            assert get_report_summary(location) == "things"

        def test_it_says_no_if_cant_find_summary(
            self, tmp_path: pathlib.Path, get_report_summary: ReportSummaryGetter
        ) -> None:
            (location := tmp_path / "one.py").write_text(
                'mod = "extended_mypy_django_plugin.version"'
            )
            assert get_report_summary(location) is None

            with open(location, "a") as fle:
                fle.write('\nsummary = "blah"')

            assert get_report_summary(location) == "blah"

        def test_it_says_no_if_cant_import_mod(
            self, tmp_path: pathlib.Path, get_report_summary: ReportSummaryGetter
        ) -> None:
            with pytest.raises(ModuleNotFoundError):
                importlib.import_module("does.not.exist")

            (location := tmp_path / "one.py").write_text(
                'mod = "does.not.exist\nsummary = "lalalala"'
            )
            assert get_report_summary(location) is None

            location.write_text('mod = "pytest"\nsummary = "ladelala"')
            assert get_report_summary(location) == "ladelala"

    class TestWrite:
        class Scenario:
            def __init__(self, discovered_project: protocols.Discovered[Project]) -> None:
                self.count: int = 0

                virtual_dependency_maker = functools.partial(
                    virtual_dependencies.VirtualDependency[Project].create,
                    virtual_dependency_namer=virtual_dependencies.VirtualDependencyNamer(
                        namespace=ImportPath("__virtual__"), hasher=adler32_hash
                    ),
                )

                self.all_virtual_dependencies = virtual_dependencies.VirtualDependencyGenerator(
                    virtual_dependency_maker=virtual_dependency_maker
                )(discovered_project=discovered_project)

            def scribe(
                self,
                *,
                hasher: protocols.Hasher,
                virtual_dependency: virtual_dependencies.VirtualDependency[Project],
            ) -> virtual_dependencies.RenderedVirtualDependency[virtual_dependencies.Report]:
                def make_differentiator() -> str:
                    self.count += 1
                    return f"__differentiated__{self.count}"

                return virtual_dependencies.VirtualDependencyScribe(
                    hasher=hasher,
                    report_maker=virtual_dependencies.Report,
                    virtual_dependency=virtual_dependency,
                    all_virtual_dependencies=self.all_virtual_dependencies,
                    installed_apps_hash="__installed_apps_hash__",
                    make_differentiator=make_differentiator,
                ).render()

            def make_report(
                self,
                *,
                concrete_annotations: dict[str, str],
                concrete_querysets: dict[str, str],
                report_import_path: dict[str, str],
            ) -> virtual_dependencies.Report:
                """
                Helper to make the tests below easier to read
                """
                return virtual_dependencies.Report(
                    concrete_annotations={
                        ImportPath(k): ImportPath(v) for k, v in concrete_annotations.items()
                    },
                    concrete_querysets={
                        ImportPath(k): ImportPath(v) for k, v in concrete_querysets.items()
                    },
                    report_import_path={
                        ImportPath(k): ImportPath(v) for k, v in report_import_path.items()
                    },
                )

        def test_writing_virtual_dependencies_1(
            self, discovered_django_example: protocols.Discovered[Project]
        ) -> None:
            scenario = self.Scenario(discovered_django_example)

            hasher_called: list[int] = []

            def hasher(*parts: bytes) -> str:
                hasher_called.append(1)
                assert parts == (
                    b"module:djangoexample.exampleapp2.models",
                    b"module:djangoexample.exampleapp2.models>concrete:djangoexample.exampleapp2.models.ChildOther=djangoexample.exampleapp2.models.ChildOther",
                    b"module:djangoexample.exampleapp2.models>concrete:djangoexample.exampleapp2.models.ChildOther2=djangoexample.exampleapp2.models.ChildOther2",
                    b"module:djangoexample.exampleapp2.models>model:djangoexample.exampleapp2.models.ChildOther>is_abstract:False",
                    b"module:djangoexample.exampleapp2.models>model:djangoexample.exampleapp2.models.ChildOther>mro_0:djangoexample.exampleapp.models.Parent",
                    b"module:djangoexample.exampleapp2.models>model:djangoexample.exampleapp2.models.ChildOther>field:id",
                    b"module:djangoexample.exampleapp2.models>model:djangoexample.exampleapp2.models.ChildOther>field:id>field_type:django.db.models.fields.BigAutoField",
                    b"module:djangoexample.exampleapp2.models>model:djangoexample.exampleapp2.models.ChildOther>field:one",
                    b"module:djangoexample.exampleapp2.models>model:djangoexample.exampleapp2.models.ChildOther>field:one>field_type:django.db.models.fields.CharField",
                    b"module:djangoexample.exampleapp2.models>model:djangoexample.exampleapp2.models.ChildOther>field:two",
                    b"module:djangoexample.exampleapp2.models>model:djangoexample.exampleapp2.models.ChildOther>field:two>field_type:django.db.models.fields.CharField",
                    b"module:djangoexample.exampleapp2.models>model:djangoexample.exampleapp2.models.ChildOther2>is_abstract:False",
                    b"module:djangoexample.exampleapp2.models>model:djangoexample.exampleapp2.models.ChildOther2>mro_0:djangoexample.exampleapp.models.Parent",
                    b"module:djangoexample.exampleapp2.models>model:djangoexample.exampleapp2.models.ChildOther2>field:id",
                    b"module:djangoexample.exampleapp2.models>model:djangoexample.exampleapp2.models.ChildOther2>field:id>field_type:django.db.models.fields.BigAutoField",
                    b"module:djangoexample.exampleapp2.models>model:djangoexample.exampleapp2.models.ChildOther2>field:one",
                    b"module:djangoexample.exampleapp2.models>model:djangoexample.exampleapp2.models.ChildOther2>field:one>field_type:django.db.models.fields.CharField",
                    b"module:djangoexample.exampleapp2.models>model:djangoexample.exampleapp2.models.ChildOther2>field:two",
                    b"module:djangoexample.exampleapp2.models>model:djangoexample.exampleapp2.models.ChildOther2>field:two>field_type:django.db.models.fields.CharField",
                )
                return "__hashed_for_great_good__"

            virtual_dependency = scenario.all_virtual_dependencies[
                ImportPath("djangoexample.exampleapp2.models")
            ]

            content = textwrap.dedent("""
            def interface____differentiated__1() -> None:
                return None

            mod = "djangoexample.exampleapp2.models"
            summary = "__virtual__.mod_3537308831::djangoexample.exampleapp2.models::installed_apps=__installed_apps_hash__::significant=__hashed_for_great_good__"

            import django.db.models
            import djangoexample.exampleapp2.models
            ConcreteQuerySet__ChildOther = django.db.models.QuerySet[djangoexample.exampleapp2.models.ChildOther]
            ConcreteQuerySet__ChildOther2 = django.db.models.QuerySet[djangoexample.exampleapp2.models.ChildOther2]
            Concrete__ChildOther = djangoexample.exampleapp2.models.ChildOther
            Concrete__ChildOther2 = djangoexample.exampleapp2.models.ChildOther2
            """).strip()

            summary_hash = (
                "__virtual__.mod_3537308831"
                "::djangoexample.exampleapp2.models"
                "::installed_apps=__installed_apps_hash__"
                "::significant=__hashed_for_great_good__"
            )

            written = scenario.scribe(hasher=hasher, virtual_dependency=virtual_dependency)
            assert written == virtual_dependencies.RenderedVirtualDependency(
                content=content + "\n",
                summary_hash=summary_hash,
                report=scenario.make_report(
                    concrete_annotations={
                        "djangoexample.exampleapp2.models.ChildOther": "__virtual__.mod_3537308831.Concrete__ChildOther",
                        "djangoexample.exampleapp2.models.ChildOther2": "__virtual__.mod_3537308831.Concrete__ChildOther2",
                    },
                    concrete_querysets={
                        "djangoexample.exampleapp2.models.ChildOther": "__virtual__.mod_3537308831.ConcreteQuerySet__ChildOther",
                        "djangoexample.exampleapp2.models.ChildOther2": "__virtual__.mod_3537308831.ConcreteQuerySet__ChildOther2",
                    },
                    report_import_path={
                        "djangoexample.exampleapp2.models": "__virtual__.mod_3537308831"
                    },
                ),
                virtual_import_path=virtual_dependency.summary.virtual_import_path,
            )

            assert hasher_called == [1]

        def test_writing_virtual_dependencies_2(
            self, discovered_django_example: protocols.Discovered[Project]
        ) -> None:
            scenario = self.Scenario(discovered_django_example)

            hasher_called: list[int] = []

            def hasher(*parts: bytes) -> str:
                hasher_called.append(1)
                assert parts == (
                    b"module:djangoexample.relations1.models",
                    b"module:djangoexample.relations1.models>concrete:djangoexample.relations1.models.Abstract=djangoexample.relations1.models.Child1,djangoexample.relations1.models.Child2",
                    b"module:djangoexample.relations1.models>concrete:djangoexample.relations1.models.Child1=djangoexample.relations1.models.Child1",
                    b"module:djangoexample.relations1.models>concrete:djangoexample.relations1.models.Child2=djangoexample.relations1.models.Child2",
                    b"module:djangoexample.relations1.models>concrete:djangoexample.relations1.models.Concrete1=djangoexample.relations1.models.Concrete1",
                    b"module:djangoexample.relations1.models>concrete:djangoexample.relations1.models.Concrete2=djangoexample.relations1.models.Concrete2",
                    b"module:djangoexample.relations1.models>model:djangoexample.relations1.models.Abstract>is_abstract:True",
                    b"module:djangoexample.relations1.models>model:djangoexample.relations1.models.Child1>is_abstract:False",
                    b"module:djangoexample.relations1.models>model:djangoexample.relations1.models.Child1>custom_queryset:djangoexample.relations1.models.Child1QuerySet",
                    b"module:djangoexample.relations1.models>model:djangoexample.relations1.models.Child1>mro_0:djangoexample.relations1.models.Abstract",
                    b"module:djangoexample.relations1.models>model:djangoexample.relations1.models.Child1>field:Concrete2_children+",
                    b"module:djangoexample.relations1.models>model:djangoexample.relations1.models.Child1>field:Concrete2_children+>field_type:django.db.models.fields.reverse_related.ManyToOneRel",
                    b"module:djangoexample.relations1.models>model:djangoexample.relations1.models.Child1>field:children",
                    b"module:djangoexample.relations1.models>model:djangoexample.relations1.models.Child1>field:children>field_type:django.db.models.fields.reverse_related.ManyToManyRel",
                    b"module:djangoexample.relations1.models>model:djangoexample.relations1.models.Child1>field:children>related_model:djangoexample.relations1.models.Concrete2",
                    b"module:djangoexample.relations1.models>model:djangoexample.relations1.models.Child1>field:id",
                    b"module:djangoexample.relations1.models>model:djangoexample.relations1.models.Child1>field:id>field_type:django.db.models.fields.BigAutoField",
                    b"module:djangoexample.relations1.models>model:djangoexample.relations1.models.Child2>is_abstract:False",
                    b"module:djangoexample.relations1.models>model:djangoexample.relations1.models.Child2>mro_0:djangoexample.relations1.models.Abstract",
                    b"module:djangoexample.relations1.models>model:djangoexample.relations1.models.Child2>field:id",
                    b"module:djangoexample.relations1.models>model:djangoexample.relations1.models.Child2>field:id>field_type:django.db.models.fields.BigAutoField",
                    b"module:djangoexample.relations1.models>model:djangoexample.relations1.models.Concrete1>is_abstract:False",
                    b"module:djangoexample.relations1.models>model:djangoexample.relations1.models.Concrete1>custom_queryset:djangoexample.relations1.models.Concrete1QuerySet",
                    b"module:djangoexample.relations1.models>model:djangoexample.relations1.models.Concrete1>field:c2s",
                    b"module:djangoexample.relations1.models>model:djangoexample.relations1.models.Concrete1>field:c2s>field_type:django.db.models.fields.reverse_related.ManyToOneRel",
                    b"module:djangoexample.relations1.models>model:djangoexample.relations1.models.Concrete1>field:c2s>related_model:djangoexample.relations1.models.Concrete2",
                    b"module:djangoexample.relations1.models>model:djangoexample.relations1.models.Concrete1>field:thing",
                    b"module:djangoexample.relations1.models>model:djangoexample.relations1.models.Concrete1>field:thing>field_type:django.db.models.fields.reverse_related.OneToOneRel",
                    b"module:djangoexample.relations1.models>model:djangoexample.relations1.models.Concrete1>field:thing>related_model:djangoexample.relations2.models.Thing",
                    b"module:djangoexample.relations1.models>model:djangoexample.relations1.models.Concrete1>field:id",
                    b"module:djangoexample.relations1.models>model:djangoexample.relations1.models.Concrete1>field:id>field_type:django.db.models.fields.BigAutoField",
                    b"module:djangoexample.relations1.models>model:djangoexample.relations1.models.Concrete2>is_abstract:False",
                    b"module:djangoexample.relations1.models>model:djangoexample.relations1.models.Concrete2>field:Concrete2_children+",
                    b"module:djangoexample.relations1.models>model:djangoexample.relations1.models.Concrete2>field:Concrete2_children+>field_type:django.db.models.fields.reverse_related.ManyToOneRel",
                    b"module:djangoexample.relations1.models>model:djangoexample.relations1.models.Concrete2>field:id",
                    b"module:djangoexample.relations1.models>model:djangoexample.relations1.models.Concrete2>field:id>field_type:django.db.models.fields.BigAutoField",
                    b"module:djangoexample.relations1.models>model:djangoexample.relations1.models.Concrete2>field:concrete1",
                    b"module:djangoexample.relations1.models>model:djangoexample.relations1.models.Concrete2>field:concrete1>field_type:django.db.models.fields.related.ForeignKey",
                    b"module:djangoexample.relations1.models>model:djangoexample.relations1.models.Concrete2>field:concrete1>related_model:djangoexample.relations1.models.Concrete1",
                    b"module:djangoexample.relations1.models>model:djangoexample.relations1.models.Concrete2>field:children",
                    b"module:djangoexample.relations1.models>model:djangoexample.relations1.models.Concrete2>field:children>field_type:django.db.models.fields.related.ManyToManyField",
                    b"module:djangoexample.relations1.models>model:djangoexample.relations1.models.Concrete2>field:children>related_model:djangoexample.relations1.models.Child1",
                )
                return "__hashed_for_greater_good__"

            virtual_dependency = scenario.all_virtual_dependencies[
                ImportPath("djangoexample.relations1.models")
            ]

            content = textwrap.dedent("""
            def interface____differentiated__1() -> None:
                return None

            mod = "djangoexample.relations1.models"
            summary = "__virtual__.mod_3327724610::djangoexample.relations1.models::installed_apps=__installed_apps_hash__::significant=__hashed_for_greater_good__"

            import django.db.models
            import djangoexample.relations1.models
            ConcreteQuerySet__Abstract = djangoexample.relations1.models.Child1QuerySet | django.db.models.QuerySet[djangoexample.relations1.models.Child2]
            ConcreteQuerySet__Child1 = djangoexample.relations1.models.Child1QuerySet
            ConcreteQuerySet__Child2 = django.db.models.QuerySet[djangoexample.relations1.models.Child2]
            ConcreteQuerySet__Concrete1 = djangoexample.relations1.models.Concrete1QuerySet
            ConcreteQuerySet__Concrete2 = django.db.models.QuerySet[djangoexample.relations1.models.Concrete2]
            Concrete__Abstract = djangoexample.relations1.models.Child1 | djangoexample.relations1.models.Child2
            Concrete__Child1 = djangoexample.relations1.models.Child1
            Concrete__Child2 = djangoexample.relations1.models.Child2
            Concrete__Concrete1 = djangoexample.relations1.models.Concrete1
            Concrete__Concrete2 = djangoexample.relations1.models.Concrete2
            """).strip()

            summary_hash = (
                "__virtual__.mod_3327724610"
                "::djangoexample.relations1.models"
                "::installed_apps=__installed_apps_hash__"
                "::significant=__hashed_for_greater_good__"
            )

            written = scenario.scribe(hasher=hasher, virtual_dependency=virtual_dependency)
            assert written == virtual_dependencies.RenderedVirtualDependency(
                content=content + "\n",
                summary_hash=summary_hash,
                report=scenario.make_report(
                    concrete_annotations={
                        "djangoexample.relations1.models.Abstract": "__virtual__.mod_3327724610.Concrete__Abstract",
                        "djangoexample.relations1.models.Child1": "__virtual__.mod_3327724610.Concrete__Child1",
                        "djangoexample.relations1.models.Child2": "__virtual__.mod_3327724610.Concrete__Child2",
                        "djangoexample.relations1.models.Concrete1": "__virtual__.mod_3327724610.Concrete__Concrete1",
                        "djangoexample.relations1.models.Concrete2": "__virtual__.mod_3327724610.Concrete__Concrete2",
                    },
                    concrete_querysets={
                        "djangoexample.relations1.models.Abstract": "__virtual__.mod_3327724610.ConcreteQuerySet__Abstract",
                        "djangoexample.relations1.models.Child1": "__virtual__.mod_3327724610.ConcreteQuerySet__Child1",
                        "djangoexample.relations1.models.Child2": "__virtual__.mod_3327724610.ConcreteQuerySet__Child2",
                        "djangoexample.relations1.models.Concrete1": "__virtual__.mod_3327724610.ConcreteQuerySet__Concrete1",
                        "djangoexample.relations1.models.Concrete2": "__virtual__.mod_3327724610.ConcreteQuerySet__Concrete2",
                    },
                    report_import_path={
                        "djangoexample.relations1.models": "__virtual__.mod_3327724610"
                    },
                ),
                virtual_import_path=virtual_dependency.summary.virtual_import_path,
            )

            assert hasher_called == [1]

        def test_writing_virtual_dependencies_3(
            self, discovered_django_example: protocols.Discovered[Project]
        ) -> None:
            scenario = self.Scenario(discovered_django_example)

            hasher_called: list[int] = []

            def hasher(*parts: bytes) -> str:
                hasher_called.append(1)
                assert parts == (b"module:djangoexample.empty_models.models",)
                return "__hashed_for_bad__"

            virtual_dependency = scenario.all_virtual_dependencies[
                ImportPath("djangoexample.empty_models.models")
            ]

            content = textwrap.dedent("""
            def interface____differentiated__1() -> None:
                return None

            mod = "djangoexample.empty_models.models"
            summary = "__virtual__.mod_3808300370::djangoexample.empty_models.models::installed_apps=__installed_apps_hash__::significant=__hashed_for_bad__"
            """).strip()

            summary_hash = (
                "__virtual__.mod_3808300370"
                "::djangoexample.empty_models.models"
                "::installed_apps=__installed_apps_hash__"
                "::significant=__hashed_for_bad__"
            )

            written = scenario.scribe(hasher=hasher, virtual_dependency=virtual_dependency)
            assert written == virtual_dependencies.RenderedVirtualDependency(
                content=content + "\n",
                summary_hash=summary_hash,
                report=virtual_dependencies.Report(
                    report_import_path={
                        ImportPath("djangoexample.empty_models.models"): ImportPath(
                            "__virtual__.mod_3808300370"
                        )
                    }
                ),
                virtual_import_path=virtual_dependency.summary.virtual_import_path,
            )

            assert hasher_called == [1]
