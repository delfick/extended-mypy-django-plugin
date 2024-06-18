import dataclasses

from extended_mypy_django_plugin.django_analysis import (
    Field,
    ImportPath,
    Model,
    protocols,
    virtual_dependencies,
)


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
            related_import_paths={
                ImportPath("M1"): {ImportPath("VM1"), ImportPath("VM2")},
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
            related_import_paths={
                ImportPath("M2"): {ImportPath("VM1"), ImportPath("VM2")},
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
            related_import_paths={
                ImportPath("M3"): {ImportPath("VM3")},
            },
        )

        final_report = virtual_dependencies.ReportCombiner(
            report_maker=virtual_dependencies.Report, reports=(report1, report2, report3)
        ).combine(version="__version__")

        assert final_report.version == "__version__"
        assert final_report.report == virtual_dependencies.Report(
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
            related_import_paths={
                ImportPath("M1"): {ImportPath("VM1"), ImportPath("VM2")},
                ImportPath("M2"): {ImportPath("VM1"), ImportPath("VM2")},
                ImportPath("M3"): {ImportPath("VM3")},
            },
        )


class TestBuildingReport:
    def test_registering_module_edits_report_import_path(self) -> None:
        report = virtual_dependencies.Report()
        report.register_module(
            module_import_path=ImportPath("one.two"),
            virtual_import_path=ImportPath("virtual.one.two"),
        )
        assert report == virtual_dependencies.Report(
            report_import_path={
                ImportPath("one.two"): ImportPath("virtual.one.two"),
            }
        )

        report.register_module(
            module_import_path=ImportPath("three.four"),
            virtual_import_path=ImportPath("virtual.three.four"),
        )
        assert report == virtual_dependencies.Report(
            report_import_path={
                ImportPath("one.two"): ImportPath("virtual.one.two"),
                ImportPath("three.four"): ImportPath("virtual.three.four"),
            }
        )

    @dataclasses.dataclass
    class BuildingScenario:
        parent: protocols.Model = dataclasses.field(
            default_factory=lambda: Model(
                model_name="Parent",
                module_import_path=ImportPath("my.parents"),
                import_path=ImportPath("my.parents.Parent"),
                is_abstract=True,
                default_custom_queryset=None,
                all_fields={},
                models_in_mro=[],
            )
        )

        def register_parent(self, report: virtual_dependencies.Report) -> None:
            report.register_model(
                model_import_path=self.parent.import_path,
                virtual_import_path=ImportPath(f"virtual.{self.parent.module_import_path}"),
                concrete_name="Concrete__Parent",
                concrete_queryset_name="QuerySet__Parent",
                concrete_models=[self.model1, self.model2],
            )

        model1: protocols.Model = dataclasses.field(
            default_factory=lambda: Model(
                model_name="Model1",
                module_import_path=ImportPath("my.models"),
                import_path=ImportPath("my.models.Model1"),
                is_abstract=False,
                default_custom_queryset=ImportPath("my.querysets.Model1QS"),
                all_fields={},
                models_in_mro=[ImportPath("my.parents.Parent")],
            )
        )

        def register_model1(self, report: virtual_dependencies.Report) -> None:
            report.register_model(
                model_import_path=self.model1.import_path,
                virtual_import_path=ImportPath(f"virtual.{self.model1.module_import_path}"),
                concrete_name="Concrete__Model1",
                concrete_queryset_name="QuerySet__Model1",
                concrete_models=[self.model1],
            )

        model2: protocols.Model = dataclasses.field(
            default_factory=lambda: Model(
                model_name="Model2",
                module_import_path=ImportPath("my.models"),
                import_path=ImportPath("my.models.Model2"),
                is_abstract=False,
                default_custom_queryset=None,
                all_fields={
                    "one": Field(
                        model_import_path=ImportPath("my.models.Model2"),
                        field_type=ImportPath("fields.Foreign"),
                        related_model=ImportPath("my.models.Model1"),
                    ),
                    "two": Field(
                        model_import_path=ImportPath("my.models.Model2"),
                        field_type=ImportPath("fields.Foreign"),
                        related_model=ImportPath("other.models.Model3"),
                    ),
                },
                models_in_mro=[ImportPath("my.parents.Parent")],
            )
        )

        def register_model2(self, report: virtual_dependencies.Report) -> None:
            report.register_model(
                model_import_path=self.model2.import_path,
                virtual_import_path=ImportPath(f"virtual.{self.model2.module_import_path}"),
                concrete_name="Concrete__Model2",
                concrete_queryset_name="QuerySet__Model2",
                concrete_models=[self.model2],
            )

        model3: protocols.Model = dataclasses.field(
            default_factory=lambda: Model(
                model_name="Model3",
                module_import_path=ImportPath("other.models"),
                import_path=ImportPath("other.models.Model3"),
                is_abstract=False,
                default_custom_queryset=ImportPath("my.querysets.Model3QS"),
                all_fields={
                    "three": Field(
                        model_import_path=ImportPath("other.models.Model3"),
                        field_type=ImportPath("fields.Foreign"),
                        related_model=ImportPath("more.models.Model4"),
                    ),
                },
                models_in_mro=[ImportPath("mixins.BlahMixin")],
            )
        )

        def register_model3(self, report: virtual_dependencies.Report) -> None:
            report.register_model(
                model_import_path=self.model3.import_path,
                virtual_import_path=ImportPath(f"virtual.{self.model3.module_import_path}"),
                concrete_name="Concrete__Model3",
                concrete_queryset_name="QuerySet__Model3",
                concrete_models=[self.model3],
            )

    def test_building_individually_parent(self) -> None:
        scenario = self.BuildingScenario()

        report = virtual_dependencies.Report()
        scenario.register_parent(report)

        assert report == virtual_dependencies.Report(
            concrete_annotations={
                ImportPath("my.parents.Parent"): ImportPath("virtual.my.parents.Concrete__Parent"),
            },
            concrete_querysets={
                ImportPath("my.parents.Parent"): ImportPath("virtual.my.parents.QuerySet__Parent"),
            },
            related_import_paths={
                ImportPath("my.parents"): {
                    ImportPath("my.models"),
                    ImportPath("my.querysets"),
                    ImportPath("other.models"),
                },
                ImportPath("my.models"): {ImportPath("my.parents")},
                ImportPath("my.querysets"): {ImportPath("my.parents")},
                ImportPath("other.models"): {ImportPath("my.parents")},
            },
        )

    def test_building_individually_model1(self) -> None:
        scenario = self.BuildingScenario()

        report = virtual_dependencies.Report()
        scenario.register_model1(report)

        assert report == virtual_dependencies.Report(
            concrete_annotations={
                ImportPath("my.models.Model1"): ImportPath("virtual.my.models.Concrete__Model1"),
            },
            concrete_querysets={
                ImportPath("my.models.Model1"): ImportPath("virtual.my.models.QuerySet__Model1"),
            },
            related_import_paths={
                ImportPath("my.parents"): {ImportPath("my.models")},
                ImportPath("my.models"): {ImportPath("my.parents"), ImportPath("my.querysets")},
                ImportPath("my.querysets"): {ImportPath("my.models")},
            },
        )

    def test_building_individually_model2(self) -> None:
        scenario = self.BuildingScenario()

        report = virtual_dependencies.Report()
        scenario.register_model2(report)

        assert report == virtual_dependencies.Report(
            concrete_annotations={
                ImportPath("my.models.Model2"): ImportPath("virtual.my.models.Concrete__Model2"),
            },
            concrete_querysets={
                ImportPath("my.models.Model2"): ImportPath("virtual.my.models.QuerySet__Model2"),
            },
            related_import_paths={
                ImportPath("my.parents"): {ImportPath("my.models")},
                ImportPath("my.models"): {ImportPath("my.parents"), ImportPath("other.models")},
                ImportPath("other.models"): {ImportPath("my.models")},
            },
        )

    def test_building_individually_model3(self) -> None:
        scenario = self.BuildingScenario()

        report = virtual_dependencies.Report()
        scenario.register_model3(report)

        assert report == virtual_dependencies.Report(
            concrete_annotations={
                ImportPath("other.models.Model3"): ImportPath(
                    "virtual.other.models.Concrete__Model3"
                ),
            },
            concrete_querysets={
                ImportPath("other.models.Model3"): ImportPath(
                    "virtual.other.models.QuerySet__Model3"
                ),
            },
            related_import_paths={
                ImportPath("mixins"): {ImportPath("other.models")},
                ImportPath("more.models"): {ImportPath("other.models")},
                ImportPath("my.querysets"): {ImportPath("other.models")},
                ImportPath("other.models"): {
                    ImportPath("mixins"),
                    ImportPath("more.models"),
                    ImportPath("my.querysets"),
                },
            },
        )

    def test_building_up_a_report(self) -> None:
        scenario = self.BuildingScenario()

        report = virtual_dependencies.Report()
        scenario.register_parent(report)

        assert report == virtual_dependencies.Report(
            concrete_annotations={
                ImportPath("my.parents.Parent"): ImportPath("virtual.my.parents.Concrete__Parent"),
            },
            concrete_querysets={
                ImportPath("my.parents.Parent"): ImportPath("virtual.my.parents.QuerySet__Parent"),
            },
            related_import_paths={
                ImportPath("my.parents"): {
                    ImportPath("my.models"),
                    ImportPath("my.querysets"),
                    ImportPath("other.models"),
                },
                ImportPath("my.models"): {ImportPath("my.parents")},
                ImportPath("my.querysets"): {ImportPath("my.parents")},
                ImportPath("other.models"): {ImportPath("my.parents")},
            },
        )

        scenario.register_model1(report)

        assert report == virtual_dependencies.Report(
            concrete_annotations={
                ImportPath("my.parents.Parent"): ImportPath("virtual.my.parents.Concrete__Parent"),
                ImportPath("my.models.Model1"): ImportPath("virtual.my.models.Concrete__Model1"),
            },
            concrete_querysets={
                ImportPath("my.parents.Parent"): ImportPath("virtual.my.parents.QuerySet__Parent"),
                ImportPath("my.models.Model1"): ImportPath("virtual.my.models.QuerySet__Model1"),
            },
            related_import_paths={
                ImportPath("my.parents"): {
                    ImportPath("my.models"),
                    ImportPath("my.querysets"),
                    ImportPath("other.models"),
                },
                ImportPath("my.models"): {ImportPath("my.parents"), ImportPath("my.querysets")},
                ImportPath("my.querysets"): {ImportPath("my.parents"), ImportPath("my.models")},
                ImportPath("other.models"): {ImportPath("my.parents")},
            },
        )

        scenario.register_model2(report)

        assert report == virtual_dependencies.Report(
            concrete_annotations={
                ImportPath("my.parents.Parent"): ImportPath("virtual.my.parents.Concrete__Parent"),
                ImportPath("my.models.Model1"): ImportPath("virtual.my.models.Concrete__Model1"),
                ImportPath("my.models.Model2"): ImportPath("virtual.my.models.Concrete__Model2"),
            },
            concrete_querysets={
                ImportPath("my.parents.Parent"): ImportPath("virtual.my.parents.QuerySet__Parent"),
                ImportPath("my.models.Model1"): ImportPath("virtual.my.models.QuerySet__Model1"),
                ImportPath("my.models.Model2"): ImportPath("virtual.my.models.QuerySet__Model2"),
            },
            related_import_paths={
                ImportPath("my.parents"): {
                    ImportPath("my.models"),
                    ImportPath("my.querysets"),
                    ImportPath("other.models"),
                },
                ImportPath("my.models"): {
                    ImportPath("my.parents"),
                    ImportPath("my.querysets"),
                    ImportPath("other.models"),
                },
                ImportPath("my.querysets"): {ImportPath("my.parents"), ImportPath("my.models")},
                ImportPath("other.models"): {ImportPath("my.models"), ImportPath("my.parents")},
            },
        )

        scenario.register_model3(report)

        assert report == virtual_dependencies.Report(
            concrete_annotations={
                ImportPath("my.parents.Parent"): ImportPath("virtual.my.parents.Concrete__Parent"),
                ImportPath("my.models.Model1"): ImportPath("virtual.my.models.Concrete__Model1"),
                ImportPath("my.models.Model2"): ImportPath("virtual.my.models.Concrete__Model2"),
                ImportPath("other.models.Model3"): ImportPath(
                    "virtual.other.models.Concrete__Model3"
                ),
            },
            concrete_querysets={
                ImportPath("my.parents.Parent"): ImportPath("virtual.my.parents.QuerySet__Parent"),
                ImportPath("my.models.Model1"): ImportPath("virtual.my.models.QuerySet__Model1"),
                ImportPath("my.models.Model2"): ImportPath("virtual.my.models.QuerySet__Model2"),
                ImportPath("other.models.Model3"): ImportPath(
                    "virtual.other.models.QuerySet__Model3"
                ),
            },
            related_import_paths={
                ImportPath("my.parents"): {
                    ImportPath("my.models"),
                    ImportPath("my.querysets"),
                    ImportPath("other.models"),
                },
                ImportPath("my.models"): {
                    ImportPath("my.parents"),
                    ImportPath("my.querysets"),
                    ImportPath("other.models"),
                },
                ImportPath("my.querysets"): {
                    ImportPath("my.parents"),
                    ImportPath("my.models"),
                    ImportPath("other.models"),
                },
                ImportPath("more.models"): {ImportPath("other.models")},
                ImportPath("other.models"): {
                    ImportPath("my.models"),
                    ImportPath("mixins"),
                    ImportPath("more.models"),
                    ImportPath("my.parents"),
                    ImportPath("my.querysets"),
                },
                ImportPath("mixins"): {ImportPath("other.models")},
            },
        )
