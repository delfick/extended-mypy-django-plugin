import dataclasses
import functools
import pathlib
from collections.abc import Iterator, Sequence
from typing import TYPE_CHECKING, Literal, cast

import pytest

from extended_mypy_django_plugin.django_analysis import (
    ImportPath,
    Module,
    Project,
    adler32_hash,
    protocols,
    virtual_dependencies,
)


class TestVirtualDependencyGenerator:
    def test_it_can_generate_virtual_dependencies(
        self, discovered_django_example: protocols.Discovered[Project]
    ) -> None:
        class CustomVirtualDependency(virtual_dependencies.VirtualDependency[Project]):
            @classmethod
            def find_significant_info_from_module(
                cls,
                *,
                discovered_project: protocols.Discovered[Project],
                module: protocols.Module,
                concrete_models: protocols.ConcreteModelsMap,
            ) -> Iterator[str]:
                yield f"__significant__{module.import_path}__"

        virtual_dependency_namer = virtual_dependencies.VirtualDependencyNamer(
            namespace=ImportPath("__virtual__"), hasher=adler32_hash
        )

        virtual_dependency_maker = functools.partial(
            CustomVirtualDependency.create, virtual_dependency_namer=virtual_dependency_namer
        )

        generated = virtual_dependencies.VirtualDependencyGenerator(
            virtual_dependency_maker=virtual_dependency_maker
        )(discovered_project=discovered_django_example)

        def IsModule(import_path: str) -> protocols.Module:
            return discovered_django_example.installed_models_modules[ImportPath(import_path)]

        def IsModel(import_path: str) -> protocols.Model:
            return discovered_django_example.all_models[ImportPath(import_path)]

        assert generated == {
            ImportPath("django.contrib.admin.models"): CustomVirtualDependency(
                module=IsModule("django.contrib.admin.models"),
                summary=virtual_dependencies.VirtualDependencySummary(
                    virtual_namespace=ImportPath("__virtual__"),
                    virtual_import_path=ImportPath("__virtual__.mod_2456226428"),
                    module_import_path=ImportPath("django.contrib.admin.models"),
                    significant_info=["__significant__django.contrib.admin.models__"],
                ),
                all_related_models=[
                    ImportPath("django.contrib.admin.models.LogEntry"),
                    ImportPath("django.contrib.auth.models.User"),
                    ImportPath("django.contrib.contenttypes.models.ContentType"),
                ],
                concrete_models={
                    ImportPath("django.contrib.admin.models.LogEntry"): [
                        IsModel("django.contrib.admin.models.LogEntry")
                    ]
                },
            ),
            ImportPath("django.contrib.auth.base_user"): CustomVirtualDependency(
                module=IsModule("django.contrib.auth.base_user"),
                summary=virtual_dependencies.VirtualDependencySummary(
                    virtual_namespace=ImportPath("__virtual__"),
                    virtual_import_path=ImportPath("__virtual__.mod_2833058650"),
                    module_import_path=ImportPath("django.contrib.auth.base_user"),
                    significant_info=["__significant__django.contrib.auth.base_user__"],
                ),
                all_related_models=[
                    ImportPath("django.contrib.auth.base_user.AbstractBaseUser"),
                ],
                concrete_models={
                    ImportPath("django.contrib.auth.base_user.AbstractBaseUser"): [
                        IsModel("django.contrib.auth.models.User")
                    ],
                },
            ),
            ImportPath("django.contrib.auth.models"): CustomVirtualDependency(
                module=IsModule("django.contrib.auth.models"),
                summary=virtual_dependencies.VirtualDependencySummary(
                    virtual_namespace=ImportPath("__virtual__"),
                    virtual_import_path=ImportPath("__virtual__.mod_2289830437"),
                    module_import_path=ImportPath("django.contrib.auth.models"),
                    significant_info=["__significant__django.contrib.auth.models__"],
                ),
                all_related_models=[
                    ImportPath("django.contrib.admin.models.LogEntry"),
                    ImportPath("django.contrib.auth.models.AbstractUser"),
                    ImportPath("django.contrib.auth.models.Group"),
                    ImportPath("django.contrib.auth.models.Permission"),
                    ImportPath("django.contrib.auth.models.PermissionsMixin"),
                    ImportPath("django.contrib.auth.models.User"),
                    ImportPath("django.contrib.contenttypes.models.ContentType"),
                ],
                concrete_models={
                    ImportPath("django.contrib.auth.models.AbstractUser"): [
                        IsModel("django.contrib.auth.models.User")
                    ],
                    ImportPath("django.contrib.auth.models.Group"): [
                        IsModel("django.contrib.auth.models.Group")
                    ],
                    ImportPath("django.contrib.auth.models.Permission"): [
                        IsModel("django.contrib.auth.models.Permission")
                    ],
                    ImportPath("django.contrib.auth.models.PermissionsMixin"): [
                        IsModel("django.contrib.auth.models.User")
                    ],
                    ImportPath("django.contrib.auth.models.User"): [
                        IsModel("django.contrib.auth.models.User")
                    ],
                },
            ),
            ImportPath("django.contrib.contenttypes.models"): CustomVirtualDependency(
                module=IsModule("django.contrib.contenttypes.models"),
                summary=virtual_dependencies.VirtualDependencySummary(
                    virtual_namespace=ImportPath("__virtual__"),
                    virtual_import_path=ImportPath("__virtual__.mod_3961720227"),
                    module_import_path=ImportPath("django.contrib.contenttypes.models"),
                    significant_info=["__significant__django.contrib.contenttypes.models__"],
                ),
                all_related_models=[
                    ImportPath("django.contrib.admin.models.LogEntry"),
                    ImportPath("django.contrib.auth.models.Permission"),
                    ImportPath("django.contrib.contenttypes.models.ContentType"),
                ],
                concrete_models={
                    ImportPath("django.contrib.contenttypes.models.ContentType"): [
                        IsModel("django.contrib.contenttypes.models.ContentType")
                    ]
                },
            ),
            ImportPath("django.contrib.sessions.base_session"): CustomVirtualDependency(
                module=IsModule("django.contrib.sessions.base_session"),
                summary=virtual_dependencies.VirtualDependencySummary(
                    virtual_namespace=ImportPath("__virtual__"),
                    virtual_import_path=ImportPath("__virtual__.mod_113708644"),
                    module_import_path=ImportPath("django.contrib.sessions.base_session"),
                    significant_info=["__significant__django.contrib.sessions.base_session__"],
                ),
                all_related_models=[
                    ImportPath("django.contrib.sessions.base_session.AbstractBaseSession"),
                ],
                concrete_models={
                    ImportPath("django.contrib.sessions.base_session.AbstractBaseSession"): [
                        IsModel("django.contrib.sessions.models.Session")
                    ]
                },
            ),
            ImportPath("django.contrib.sessions.models"): CustomVirtualDependency(
                module=IsModule("django.contrib.sessions.models"),
                summary=virtual_dependencies.VirtualDependencySummary(
                    virtual_namespace=ImportPath("__virtual__"),
                    virtual_import_path=ImportPath("__virtual__.mod_3074165738"),
                    module_import_path=ImportPath("django.contrib.sessions.models"),
                    significant_info=["__significant__django.contrib.sessions.models__"],
                ),
                all_related_models=[
                    ImportPath("django.contrib.sessions.models.Session"),
                ],
                concrete_models={
                    ImportPath("django.contrib.sessions.models.Session"): [
                        IsModel("django.contrib.sessions.models.Session")
                    ],
                },
            ),
            ImportPath("djangoexample.exampleapp.models"): CustomVirtualDependency(
                module=IsModule("djangoexample.exampleapp.models"),
                summary=virtual_dependencies.VirtualDependencySummary(
                    virtual_namespace=ImportPath("__virtual__"),
                    virtual_import_path=ImportPath("__virtual__.mod_3347844205"),
                    module_import_path=ImportPath("djangoexample.exampleapp.models"),
                    significant_info=["__significant__djangoexample.exampleapp.models__"],
                ),
                all_related_models=[
                    ImportPath("djangoexample.exampleapp.models.Child1"),
                    ImportPath("djangoexample.exampleapp.models.Child2"),
                    ImportPath("djangoexample.exampleapp.models.Child3"),
                    ImportPath("djangoexample.exampleapp.models.Child4"),
                    ImportPath("djangoexample.exampleapp.models.Parent"),
                    ImportPath("djangoexample.exampleapp.models.Parent2"),
                ],
                concrete_models={
                    ImportPath("djangoexample.exampleapp.models.Child1"): [
                        IsModel("djangoexample.exampleapp.models.Child1"),
                    ],
                    ImportPath("djangoexample.exampleapp.models.Child2"): [
                        IsModel("djangoexample.exampleapp.models.Child2")
                    ],
                    ImportPath("djangoexample.exampleapp.models.Child3"): [
                        IsModel("djangoexample.exampleapp.models.Child3")
                    ],
                    ImportPath("djangoexample.exampleapp.models.Child4"): [
                        IsModel("djangoexample.exampleapp.models.Child4")
                    ],
                    ImportPath("djangoexample.exampleapp.models.Parent"): [
                        IsModel("djangoexample.exampleapp.models.Child1"),
                        IsModel("djangoexample.exampleapp.models.Child2"),
                        IsModel("djangoexample.exampleapp.models.Child3"),
                        IsModel("djangoexample.exampleapp.models.Child4"),
                        IsModel("djangoexample.exampleapp2.models.ChildOther"),
                        IsModel("djangoexample.exampleapp2.models.ChildOther2"),
                    ],
                    ImportPath("djangoexample.exampleapp.models.Parent2"): [
                        IsModel("djangoexample.exampleapp.models.Child3"),
                        IsModel("djangoexample.exampleapp.models.Child4"),
                    ],
                },
            ),
            ImportPath("djangoexample.exampleapp2.models"): CustomVirtualDependency(
                module=IsModule("djangoexample.exampleapp2.models"),
                summary=virtual_dependencies.VirtualDependencySummary(
                    virtual_namespace=ImportPath("__virtual__"),
                    virtual_import_path=ImportPath("__virtual__.mod_3537308831"),
                    module_import_path=ImportPath("djangoexample.exampleapp2.models"),
                    significant_info=["__significant__djangoexample.exampleapp2.models__"],
                ),
                all_related_models=[
                    ImportPath("djangoexample.exampleapp2.models.ChildOther"),
                    ImportPath("djangoexample.exampleapp2.models.ChildOther2"),
                ],
                concrete_models={
                    ImportPath("djangoexample.exampleapp2.models.ChildOther"): [
                        IsModel("djangoexample.exampleapp2.models.ChildOther")
                    ],
                    ImportPath("djangoexample.exampleapp2.models.ChildOther2"): [
                        IsModel("djangoexample.exampleapp2.models.ChildOther2"),
                    ],
                },
            ),
            ImportPath("djangoexample.only_abstract.models"): CustomVirtualDependency(
                module=IsModule("djangoexample.only_abstract.models"),
                summary=virtual_dependencies.VirtualDependencySummary(
                    virtual_namespace=ImportPath("__virtual__"),
                    virtual_import_path=ImportPath("__virtual__.mod_4035906997"),
                    module_import_path=ImportPath("djangoexample.only_abstract.models"),
                    significant_info=["__significant__djangoexample.only_abstract.models__"],
                ),
                all_related_models=[
                    ImportPath("djangoexample.only_abstract.models.AnAbstract"),
                ],
                concrete_models={
                    ImportPath("djangoexample.only_abstract.models.AnAbstract"): [],
                },
            ),
            ImportPath("djangoexample.relations1.models"): CustomVirtualDependency(
                module=IsModule("djangoexample.relations1.models"),
                summary=virtual_dependencies.VirtualDependencySummary(
                    virtual_namespace=ImportPath("__virtual__"),
                    virtual_import_path=ImportPath("__virtual__.mod_3327724610"),
                    module_import_path=ImportPath("djangoexample.relations1.models"),
                    significant_info=["__significant__djangoexample.relations1.models__"],
                ),
                all_related_models=[
                    ImportPath("djangoexample.relations1.models.Abstract"),
                    ImportPath("djangoexample.relations1.models.Child1"),
                    ImportPath("djangoexample.relations1.models.Child2"),
                    ImportPath("djangoexample.relations1.models.Concrete1"),
                    ImportPath("djangoexample.relations1.models.Concrete2"),
                    ImportPath("djangoexample.relations2.models.Thing"),
                ],
                concrete_models={
                    ImportPath("djangoexample.relations1.models.Abstract"): [
                        IsModel("djangoexample.relations1.models.Child1"),
                        IsModel("djangoexample.relations1.models.Child2"),
                    ],
                    ImportPath("djangoexample.relations1.models.Child1"): [
                        IsModel("djangoexample.relations1.models.Child1"),
                    ],
                    ImportPath("djangoexample.relations1.models.Child2"): [
                        IsModel("djangoexample.relations1.models.Child2"),
                    ],
                    ImportPath("djangoexample.relations1.models.Concrete1"): [
                        IsModel("djangoexample.relations1.models.Concrete1"),
                    ],
                    ImportPath("djangoexample.relations1.models.Concrete2"): [
                        IsModel("djangoexample.relations1.models.Concrete2"),
                    ],
                },
            ),
            ImportPath("djangoexample.relations2.models"): CustomVirtualDependency(
                module=IsModule("djangoexample.relations2.models"),
                summary=virtual_dependencies.VirtualDependencySummary(
                    virtual_namespace=ImportPath("__virtual__"),
                    virtual_import_path=ImportPath("__virtual__.mod_3328248899"),
                    module_import_path=ImportPath("djangoexample.relations2.models"),
                    significant_info=["__significant__djangoexample.relations2.models__"],
                ),
                all_related_models=[
                    ImportPath("djangoexample.relations1.models.Concrete1"),
                    ImportPath("djangoexample.relations2.models.Thing"),
                ],
                concrete_models={
                    ImportPath("djangoexample.relations2.models.Thing"): [
                        IsModel("djangoexample.relations2.models.Thing")
                    ],
                },
            ),
            ImportPath("djangoexample.empty_models.models"): CustomVirtualDependency(
                module=IsModule("djangoexample.empty_models.models"),
                summary=virtual_dependencies.VirtualDependencySummary(
                    virtual_namespace=ImportPath("__virtual__"),
                    virtual_import_path=ImportPath("__virtual__.mod_3808300370"),
                    module_import_path=ImportPath("djangoexample.empty_models.models"),
                    significant_info=["__significant__djangoexample.empty_models.models__"],
                ),
                all_related_models=[],
                concrete_models={},
            ),
        }


class TestVirtualDependencyInstaller:
    def test_it_uses_the_report_factory(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        scratch_root = tmp_path_factory.mktemp("scratch_root")
        destination = tmp_path_factory.mktemp("destination")

        installed: list[tuple[pathlib.Path, pathlib.Path, protocols.ImportPath]] = []
        written: dict[
            tuple[pathlib.Path, protocols.ImportPath], tuple[str, str | Literal[False] | None]
        ] = {}

        virtual_dependency_namer = virtual_dependencies.VirtualDependencyNamer(
            namespace=ImportPath("__virtual__"), hasher=adler32_hash
        )

        class Dep(virtual_dependencies.VirtualDependency[Project]):
            pass

        @dataclasses.dataclass
        class Report:
            modules: set[tuple[protocols.ImportPath, protocols.ImportPath]] = dataclasses.field(
                default_factory=set
            )
            combined: bool = False

            def register_module(
                self,
                *,
                module_import_path: protocols.ImportPath,
                virtual_import_path: protocols.ImportPath,
            ) -> None:
                self.modules.add((module_import_path, virtual_import_path))

            def register_model(
                self,
                *,
                model_import_path: protocols.ImportPath,
                virtual_import_path: protocols.ImportPath,
                concrete_name: str,
                concrete_queryset_name: str,
                concrete_models: Sequence[protocols.Model],
            ) -> None:
                raise ValueError("not called")

        @dataclasses.dataclass
        class ReportCombiner:
            reports: Sequence[Report]

            def combine(
                self, *, version: str, write_empty_virtual_dep: protocols.EmptyVirtualDepWriter
            ) -> protocols.CombinedReport[Report]:
                final = Report(combined=True)
                for report in self.reports:
                    final.modules |= report.modules

                return virtual_dependencies.CombinedReport(
                    version=version, report=final, write_empty_virtual_dep=write_empty_virtual_dep
                )

        @dataclasses.dataclass
        class ReportInstaller:
            def write_report(
                self,
                *,
                scratch_root: pathlib.Path,
                summary_hash: str | Literal[False] | None,
                virtual_import_path: protocols.ImportPath,
                content: str,
            ) -> bool:
                key = (scratch_root, virtual_import_path)
                exists = any(v == virtual_import_path for _, v in written)
                if exists and summary_hash is False:
                    return False
                assert not exists
                written[key] = (content, summary_hash)
                return True

            def install_reports(
                self,
                *,
                scratch_root: pathlib.Path,
                destination: pathlib.Path,
                virtual_namespace: protocols.ImportPath,
            ) -> None:
                installed.append((scratch_root, destination, virtual_namespace))

        class ReportFactory:
            def __init__(self) -> None:
                self.report_installer = ReportInstaller()
                self.report_maker = Report
                self.report_combiner_maker = ReportCombiner

            def deploy_scribes(
                self, all_virtual_dependencies: protocols.VirtualDependencyMap[Dep]
            ) -> Iterator[protocols.RenderedVirtualDependency[Report]]:
                for virtual_dependency in all_virtual_dependencies.values():
                    report = self.report_maker()
                    report.register_module(
                        module_import_path=virtual_dependency.summary.module_import_path,
                        virtual_import_path=virtual_dependency.summary.virtual_import_path,
                    )
                    yield virtual_dependencies.RenderedVirtualDependency(
                        content=f"CONTENT__{virtual_dependency.summary.module_import_path}",
                        summary_hash=f"SUMMARY__{virtual_dependency.summary.module_import_path}",
                        report=report,
                        virtual_import_path=virtual_dependency.summary.virtual_import_path,
                    )

            def make_empty_virtual_dependency_content(
                self, *, module_import_path: protocols.ImportPath
            ) -> str:
                return "empty"

            def determine_version(
                self,
                *,
                destination: pathlib.Path,
                virtual_namespace: protocols.ImportPath,
                project_version: str,
                written_dependencies: Sequence[
                    protocols.RenderedVirtualDependency[protocols.T_Report]
                ],
            ) -> str:
                assert project_version == "__project_version__"
                assert virtual_namespace == ImportPath("__virtual__")
                return "__version__"

        if TYPE_CHECKING:
            _D: protocols.VirtualDependency = cast(Dep, None)
            _R: protocols.Report = cast(Report, None)
            _RC: protocols.ReportCombiner[Report] = cast(ReportCombiner, None)
            _RCM: protocols.ReportCombinerMaker[Report] = ReportCombiner
            _RI: protocols.ReportInstaller = cast(ReportInstaller, None)
            _RF: protocols.ReportFactory[Dep, Report] = cast(ReportFactory, None)

        installer = virtual_dependencies.VirtualDependencyInstaller[Dep, Report](
            project_version="__project_version__",
            virtual_dependency_namer=virtual_dependency_namer,
            virtual_dependencies={
                ImportPath("M1.models"): Dep(
                    module=Module(import_path=ImportPath("M1.models"), defined_models={}),
                    summary=virtual_dependencies.VirtualDependencySummary(
                        virtual_namespace=ImportPath("__virtual__"),
                        virtual_import_path=ImportPath("__virtual__.mod_239797041"),
                        module_import_path=ImportPath("M1"),
                        significant_info=["__significant__django.contrib.admin.models__"],
                    ),
                    all_related_models=[],
                    concrete_models={},
                ),
                ImportPath("M2"): Dep(
                    module=Module(import_path=ImportPath("M2"), defined_models={}),
                    summary=virtual_dependencies.VirtualDependencySummary(
                        virtual_namespace=ImportPath("__virtual__"),
                        virtual_import_path=ImportPath("__virtual__.M2"),
                        module_import_path=ImportPath("M2"),
                        significant_info=["__significant__django.contrib.admin.models__"],
                    ),
                    all_related_models=[],
                    concrete_models={},
                ),
            },
        )

        assert written == {}
        assert installed == []
        report = installer(
            scratch_root=scratch_root,
            destination=destination,
            virtual_namespace=ImportPath("__virtual__"),
            report_factory=ReportFactory(),
        )

        assert report.version == "__version__"
        assert report.report == Report(
            combined=True,
            modules={
                (ImportPath("M1"), ImportPath("__virtual__.mod_239797041")),
                (ImportPath("M2"), ImportPath("__virtual__.M2")),
            },
        )

        assert written == {
            (scratch_root, ImportPath("__virtual__.mod_239797041")): (
                "CONTENT__M1",
                "SUMMARY__M1",
            ),
            (scratch_root, ImportPath("__virtual__.M2")): ("CONTENT__M2", "SUMMARY__M2"),
        }
        assert installed == [(scratch_root, destination, ImportPath("__virtual__"))]

        report.ensure_virtual_dependency(module_import_path="E1.models")
        assert (
            ImportPath("E1.models"),
            ImportPath("__virtual__.mod_235078441"),
        ) in report.report.modules
        assert written == {
            (scratch_root, ImportPath("__virtual__.mod_239797041")): (
                "CONTENT__M1",
                "SUMMARY__M1",
            ),
            (scratch_root, ImportPath("__virtual__.M2")): ("CONTENT__M2", "SUMMARY__M2"),
            # The empty dep is written directly to the final destination
            # cause it happens at mypy time
            (destination, ImportPath("__virtual__.mod_235078441")): ("empty", False),
        }

        # Existing modules are not overridden
        report.ensure_virtual_dependency(module_import_path="M1.models")
        assert written == {
            # We want the content for M1 to have not been changed in destination
            (scratch_root, ImportPath("__virtual__.mod_239797041")): (
                "CONTENT__M1",
                "SUMMARY__M1",
            ),
            (scratch_root, ImportPath("__virtual__.M2")): ("CONTENT__M2", "SUMMARY__M2"),
            (destination, ImportPath("__virtual__.mod_235078441")): ("empty", False),
        }
        assert report.report.modules == {
            (ImportPath("M1"), ImportPath("__virtual__.mod_239797041")),
            (ImportPath("M2"), ImportPath("__virtual__.M2")),
            (ImportPath("E1.models"), ImportPath("__virtual__.mod_235078441")),
        }
