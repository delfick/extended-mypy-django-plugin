from __future__ import annotations

import collections
import dataclasses
import functools
import pathlib
from collections.abc import MutableMapping, MutableSet, Sequence
from typing import TYPE_CHECKING, Generic, TypeVar, cast

from .. import project, protocols
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
        pass

    def register_model(
        self,
        *,
        model_import_path: protocols.ImportPath,
        virtual_import_path: protocols.ImportPath,
        concrete_name: str,
        concrete_queryset_name: str,
        concrete_models: Sequence[protocols.Model],
    ) -> None:
        pass


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

    def generate_report(self) -> WrittenVirtualDependency[protocols.T_Report]:
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
class ReportFactory(
    Generic[protocols.T_Project, protocols.T_VirtualDependency, protocols.T_Report]
):
    report_installer: protocols.ReportInstaller
    virtual_dependency_scribe_maker: protocols.VirtualDependencyScribeMaker[
        protocols.T_VirtualDependency, protocols.T_Report
    ]
    report_combiner_maker: protocols.ReportCombinerMaker[protocols.T_Report]
    report_maker: protocols.ReportMaker[protocols.T_Report]


def make_report_factory(
    *,
    discovered_project: protocols.Discovered[protocols.T_Project],
    hasher: protocols.Hasher,
) -> protocols.ReportFactory[dependency.VirtualDependency[protocols.T_Project], Report]:
    return ReportFactory(
        report_maker=Report,
        virtual_dependency_scribe_maker=functools.partial(
            VirtualDependencyScribe,
            hasher=hasher,
            discovered_project=discovered_project,
            report_maker=Report,
        ),
        report_installer=ReportInstaller(),
        report_combiner_maker=functools.partial(ReportCombiner, report_maker=Report),
    )


if TYPE_CHECKING:
    C_Report = Report
    C_ReportFactory = ReportFactory[project.C_Project, dependency.C_VirtualDependency, C_Report]
    C_ReportCombiner = ReportCombiner[C_Report]
    C_ReportInstaller = ReportInstaller
    C_VirtualDependencyScribe = VirtualDependencyScribe[project.C_Project, C_Report]
    C_WrittenVirtualDependency = WrittenVirtualDependency

    _R: protocols.Report = cast(Report, None)
    _WVD: protocols.WrittenVirtualDependency[protocols.P_Report] = cast(
        WrittenVirtualDependency[protocols.P_Report], None
    )
    _RM: protocols.P_VirtualDependencyScribe = cast(
        VirtualDependencyScribe[protocols.P_Project, protocols.P_Report], None
    )
    _RI: protocols.P_ReportInstaller = cast(ReportInstaller, None)

    _CVDS: protocols.VirtualDependencyScribe[dependency.C_VirtualDependency, C_Report] = cast(
        VirtualDependencyScribe[project.C_Project, C_Report], None
    )
    _CRC: protocols.ReportCombiner[C_Report] = cast(C_ReportCombiner, None)
    _CRF: protocols.ReportFactory[dependency.C_VirtualDependency, C_Report] = cast(
        ReportFactory[project.C_Project, dependency.C_VirtualDependency, C_Report], None
    )
    _CRM: protocols.ReportMaker[C_Report] = Report
    _CWVD: protocols.WrittenVirtualDependency[C_Report] = cast(
        WrittenVirtualDependency[C_Report], None
    )
