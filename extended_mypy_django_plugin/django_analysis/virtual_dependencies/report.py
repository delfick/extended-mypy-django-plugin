from __future__ import annotations

import dataclasses
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Generic, cast

from .. import protocols


@dataclasses.dataclass(frozen=True, kw_only=True)
class Report:
    concrete_annotations: Mapping[protocols.ImportPath, protocols.ImportPath]
    concrete_querysets: Mapping[protocols.ImportPath, protocols.ImportPath]
    report_import_path: Mapping[protocols.ImportPath, protocols.ImportPath]
    related_report_import_paths: Mapping[protocols.ImportPath, Sequence[protocols.ImportPath]]


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

    _R: protocols.Report = cast(Report, None)

    _CRC: protocols.ReportCombiner[C_Report] = cast(C_ReportCombiner, None)
    _CRM: protocols.ReportMaker[C_Report] = Report
