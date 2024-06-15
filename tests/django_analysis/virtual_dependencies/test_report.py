from extended_mypy_django_plugin.django_analysis import ImportPath, virtual_dependencies


class TestCombiningReports:
    def test_it_can_combine_reports(self) -> None:
        report1 = virtual_dependencies.Report(
            concrete_annotations={
                ImportPath("P1"): ImportPath("CP1"),
                ImportPath("C1"): ImportPath("CC1"),
            },
            concrete_querysets={
                ImportPath("P1"): ImportPath("CP1QS"),
                ImportPath("C1"): ImportPath("CC1QS"),
            },
            report_import_path={
                ImportPath("M1"): ImportPath("VM1"),
            },
            related_report_import_paths={
                ImportPath("M1"): [ImportPath("VM1"), ImportPath("VM2")],
            },
        )
        report2 = virtual_dependencies.Report(
            concrete_annotations={
                ImportPath("C2"): ImportPath("CC2"),
            },
            concrete_querysets={
                ImportPath("C2"): ImportPath("C2QS"),
            },
            report_import_path={
                ImportPath("M2"): ImportPath("VM2"),
            },
            related_report_import_paths={
                ImportPath("M2"): [ImportPath("VM1"), ImportPath("VM2")],
            },
        )
        report3 = virtual_dependencies.Report(
            concrete_annotations={
                ImportPath("P2"): ImportPath("CP2"),
                ImportPath("C3"): ImportPath("CC3"),
                ImportPath("C4"): ImportPath("CC4"),
            },
            concrete_querysets={
                ImportPath("P2"): ImportPath("CP2QS"),
                ImportPath("C3"): ImportPath("CC3QS"),
                ImportPath("C4"): ImportPath("CC4QS"),
            },
            report_import_path={
                ImportPath("M3"): ImportPath("VM3"),
            },
            related_report_import_paths={
                ImportPath("M3"): [ImportPath("VM3")],
            },
        )

        final_report = virtual_dependencies.ReportCombiner(
            report_maker=virtual_dependencies.Report, reports=(report1, report2, report3)
        ).combine()

        assert final_report == virtual_dependencies.Report(
            concrete_annotations={
                ImportPath("P1"): ImportPath("CP1"),
                ImportPath("C1"): ImportPath("CC1"),
                ImportPath("C2"): ImportPath("CC2"),
                ImportPath("P2"): ImportPath("CP2"),
                ImportPath("C3"): ImportPath("CC3"),
                ImportPath("C4"): ImportPath("CC4"),
            },
            concrete_querysets={
                ImportPath("P1"): ImportPath("CP1QS"),
                ImportPath("C1"): ImportPath("CC1QS"),
                ImportPath("C2"): ImportPath("C2QS"),
                ImportPath("P2"): ImportPath("CP2QS"),
                ImportPath("C3"): ImportPath("CC3QS"),
                ImportPath("C4"): ImportPath("CC4QS"),
            },
            report_import_path={
                ImportPath("M1"): ImportPath("VM1"),
                ImportPath("M2"): ImportPath("VM2"),
                ImportPath("M3"): ImportPath("VM3"),
            },
            related_report_import_paths={
                ImportPath("M1"): [ImportPath("VM1"), ImportPath("VM2")],
                ImportPath("M2"): [ImportPath("VM1"), ImportPath("VM2")],
                ImportPath("M3"): [ImportPath("VM3")],
            },
        )
