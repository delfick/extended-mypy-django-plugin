from __future__ import annotations

import dataclasses
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


@dataclasses.dataclass
class VirtualDependencyScribe(Generic[protocols.T_Project, protocols.T_Report]):
    hasher: protocols.Hasher
    report_maker: protocols.ReportMaker[protocols.T_Report]
    discovered_project: protocols.Discovered[protocols.T_Project]
    virtual_dependency: dependency.VirtualDependency[protocols.T_Project]

    def generate_report(self) -> tuple[str, protocols.T_Report, protocols.ImportPath]:
        report = self.report_maker(
            concrete_annotations={},
            concrete_querysets={},
            report_import_path={},
            related_report_import_paths={},
        )
        virtual_import_path = report.report_import_path[self.virtual_dependency.module.import_path]
        return "", report, virtual_import_path


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


if TYPE_CHECKING:
    C_Report = Report
    C_ReportCombiner = ReportCombiner[C_Report]
    C_VirtualDependencyScribe = VirtualDependencyScribe[project.C_Project, C_Report]

    _R: protocols.Report = cast(Report, None)
    _RM: protocols.P_VirtualDependencyScribe = cast(
        VirtualDependencyScribe[protocols.P_Project, protocols.P_Report], None
    )

    _CVDS: protocols.VirtualDependencyScribe[dependency.C_VirtualDependency, C_Report] = cast(
        VirtualDependencyScribe[project.C_Project, C_Report], None
    )
    _CRC: protocols.ReportCombiner[C_Report] = cast(C_ReportCombiner, None)
    _CRM: protocols.ReportMaker[C_Report] = Report
