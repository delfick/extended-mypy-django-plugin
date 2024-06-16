from __future__ import annotations

import collections
import dataclasses
import functools
import pathlib
from collections.abc import Iterator, MutableMapping, MutableSet, Sequence
from typing import TYPE_CHECKING, Generic, TypeVar, cast

from .. import project, protocols
from ..discovery import ImportPath
from . import dependency

T_Report = TypeVar("T_Report", bound="Report")


@dataclasses.dataclass(frozen=True, kw_only=True)
class Report:
    concrete_annotations: MutableMapping[protocols.ImportPath, protocols.ImportPath] = (
        dataclasses.field(default_factory=dict)
    )
    concrete_querysets: MutableMapping[protocols.ImportPath, protocols.ImportPath] = (
        dataclasses.field(default_factory=dict)
    )
    report_import_path: MutableMapping[protocols.ImportPath, protocols.ImportPath] = (
        dataclasses.field(default_factory=dict)
    )
    related_import_paths: MutableMapping[
        protocols.ImportPath, MutableSet[protocols.ImportPath]
    ] = dataclasses.field(default_factory=lambda: collections.defaultdict(set))

    def register_module(
        self,
        *,
        module_import_path: protocols.ImportPath,
        virtual_import_path: protocols.ImportPath,
    ) -> None:
        self.report_import_path[module_import_path] = virtual_import_path

    def register_model(
        self,
        *,
        model_import_path: protocols.ImportPath,
        virtual_import_path: protocols.ImportPath,
        concrete_name: str,
        concrete_queryset_name: str,
        concrete_models: Sequence[protocols.Model],
    ) -> None:
        module_import_path, name = ImportPath.split(model_import_path)

        self.concrete_annotations[model_import_path] = ImportPath(
            f"{virtual_import_path}.{concrete_name}"
        )
        self.concrete_querysets[model_import_path] = ImportPath(
            f"{virtual_import_path}.{concrete_queryset_name}"
        )

        for concrete in concrete_models:
            ns, _ = ImportPath.split(concrete.import_path)
            if ns != module_import_path:
                self.related_import_paths[module_import_path].add(ns)
                self.related_import_paths[ns].add(module_import_path)

            if concrete.default_custom_queryset:
                ns, _ = ImportPath.split(concrete.default_custom_queryset)
                if ns != module_import_path:
                    self.related_import_paths[module_import_path].add(ns)
                    self.related_import_paths[ns].add(module_import_path)

            for field in concrete.all_fields.values():
                if field.related_model:
                    ns, _ = ImportPath.split(field.related_model)
                    if ns != module_import_path:
                        self.related_import_paths[module_import_path].add(ns)
                        self.related_import_paths[ns].add(module_import_path)

            for mro in concrete.models_in_mro:
                ns, _ = ImportPath.split(mro)
                if ns != module_import_path:
                    self.related_import_paths[module_import_path].add(ns)
                    self.related_import_paths[ns].add(module_import_path)


@dataclasses.dataclass(frozen=True, kw_only=True)
class WrittenVirtualDependency(Generic[protocols.T_Report]):
    content: str
    summary_hash: str | None
    report: protocols.T_Report
    virtual_import_path: protocols.ImportPath


@dataclasses.dataclass(frozen=True, kw_only=True)
class VirtualDependencyScribe(Generic[protocols.T_Project, protocols.T_Report]):
    hasher: protocols.Hasher
    report_maker: protocols.ReportMaker[protocols.T_Report]
    discovered_project: protocols.Discovered[protocols.T_Project]
    virtual_dependency: dependency.VirtualDependency[protocols.T_Project]
    all_virtual_dependencies: protocols.VirtualDependencyMap[
        dependency.VirtualDependency[protocols.T_Project]
    ]

    def write(self) -> WrittenVirtualDependency[protocols.T_Report]:
        report = self.report_maker()
        virtual_import_path = self.virtual_dependency.summary.virtual_dependency_name
        return WrittenVirtualDependency(
            content="", summary_hash="", report=report, virtual_import_path=virtual_import_path
        )


@dataclasses.dataclass(frozen=True, kw_only=True)
class ReportCombiner(Generic[T_Report]):
    reports: Sequence[T_Report]
    report_maker: protocols.ReportMaker[T_Report]

    def combine(self) -> T_Report:
        final = self.report_maker()
        for report in self.reports:
            final.concrete_annotations.update(report.concrete_annotations)
            final.concrete_querysets.update(report.concrete_querysets)
            final.report_import_path.update(report.report_import_path)

            for path, related in report.related_import_paths.items():
                final.related_import_paths[path] |= related

        return final


@dataclasses.dataclass(frozen=True, kw_only=True)
class ReportInstaller:
    def write_report(
        self,
        *,
        scratch_root: pathlib.Path,
        virtual_import_path: protocols.ImportPath,
        summary_hash: str | None,
        content: str,
    ) -> None:
        pass

    def install_reports(self, *, scratch_root: pathlib.Path, destination: pathlib.Path) -> None:
        pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class ReportFactory(Generic[protocols.T_Project, protocols.T_VirtualDependency, T_Report]):
    report_installer: protocols.ReportInstaller
    report_combiner_maker: protocols.ReportCombinerMaker[T_Report]
    report_maker: protocols.ReportMaker[T_Report]
    report_scribe: protocols.VirtualDependencyScribe[protocols.T_VirtualDependency, T_Report]

    def deploy_scribes(
        self, virtual_dependencies: protocols.VirtualDependencyMap[protocols.T_VirtualDependency]
    ) -> Iterator[protocols.WrittenVirtualDependency[T_Report]]:
        for virtual_dependency in virtual_dependencies.values():
            yield self.report_scribe(
                virtual_dependency=virtual_dependency,
                all_virtual_dependencies=virtual_dependencies,
            )


def make_report_factory(
    *, discovered_project: protocols.Discovered[protocols.T_Project], hasher: protocols.Hasher
) -> protocols.ReportFactory[dependency.VirtualDependency[protocols.T_Project], Report]:
    def report_scribe(
        *,
        virtual_dependency: dependency.VirtualDependency[protocols.T_Project],
        all_virtual_dependencies: protocols.VirtualDependencyMap[
            dependency.VirtualDependency[protocols.T_Project]
        ],
    ) -> protocols.WrittenVirtualDependency[Report]:
        return VirtualDependencyScribe(
            hasher=hasher,
            discovered_project=discovered_project,
            report_maker=Report,
            virtual_dependency=virtual_dependency,
            all_virtual_dependencies=all_virtual_dependencies,
        ).write()

    return ReportFactory(
        report_maker=Report,
        report_scribe=report_scribe,
        report_installer=ReportInstaller(),
        report_combiner_maker=functools.partial(ReportCombiner, report_maker=Report),
    )


if TYPE_CHECKING:
    C_Report = Report
    C_ReportFactory = ReportFactory[project.C_Project, dependency.C_VirtualDependency, C_Report]
    C_ReportCombiner = ReportCombiner[C_Report]
    C_ReportInstaller = ReportInstaller
    C_WrittenVirtualDependency = WrittenVirtualDependency[C_Report]

    _R: protocols.Report = cast(Report, None)
    _WVD: protocols.WrittenVirtualDependency[protocols.P_Report] = cast(
        WrittenVirtualDependency[protocols.P_Report], None
    )
    _RI: protocols.P_ReportInstaller = cast(ReportInstaller, None)

    _CRC: protocols.ReportCombiner[C_Report] = cast(C_ReportCombiner, None)
    _CRF: protocols.ReportFactory[dependency.C_VirtualDependency, C_Report] = cast(
        C_ReportFactory, None
    )
    _CRM: protocols.ReportMaker[C_Report] = C_Report
    _CWVD: protocols.WrittenVirtualDependency[C_Report] = cast(C_WrittenVirtualDependency, None)
