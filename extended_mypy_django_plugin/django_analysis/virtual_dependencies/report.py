from __future__ import annotations

import dataclasses
import functools
import pathlib
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Generic, cast

from .. import project, protocols
from . import dependency


@dataclasses.dataclass(frozen=True, kw_only=True)
class Report:
    concrete_annotations: Mapping[protocols.ImportPath, protocols.ImportPath]
    concrete_querysets: Mapping[protocols.ImportPath, protocols.ImportPath]
    report_import_path: Mapping[protocols.ImportPath, protocols.ImportPath]
    related_report_import_paths: Mapping[protocols.ImportPath, Sequence[protocols.ImportPath]]


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
        report = self.report_maker(
            concrete_annotations={},
            concrete_querysets={},
            report_import_path={},
            related_report_import_paths={},
        )
        virtual_import_path = report.report_import_path[self.virtual_dependency.module.import_path]
        return WrittenVirtualDependency(
            content="", summary_hash="", report=report, virtual_import_path=virtual_import_path
        )


@dataclasses.dataclass(frozen=True, kw_only=True)
class ReportCombiner(Generic[protocols.T_Report]):
    reports: Sequence[protocols.T_Report]
    report_maker: protocols.ReportMaker[protocols.T_Report]

    def combine(self) -> protocols.T_Report:
        concrete_annotations: dict[protocols.ImportPath, protocols.ImportPath] = {}
        concrete_querysets: dict[protocols.ImportPath, protocols.ImportPath] = {}
        report_import_path: dict[protocols.ImportPath, protocols.ImportPath] = {}
        related_report_import_paths: dict[
            protocols.ImportPath, Sequence[protocols.ImportPath]
        ] = {}

        for report in self.reports:
            concrete_annotations.update(report.concrete_annotations)
            concrete_querysets.update(report.concrete_querysets)
            report_import_path.update(report.report_import_path)
            related_report_import_paths.update(report.related_report_import_paths)

        return self.report_maker(
            concrete_annotations=concrete_annotations,
            concrete_querysets=concrete_querysets,
            report_import_path=report_import_path,
            related_report_import_paths=related_report_import_paths,
        )


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
