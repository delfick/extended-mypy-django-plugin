import dataclasses

import pytest

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
        )

        def write_empty_virtual_dep(
            *, module_import_path: protocols.ImportPath
        ) -> protocols.ImportPath | None:
            raise NotImplementedError()

        final_report = virtual_dependencies.ReportCombiner(
            report_maker=virtual_dependencies.Report, reports=(report1, report2, report3)
        ).combine(version="__version__", write_empty_virtual_dep=write_empty_virtual_dep)

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
        )

    def test_it_can_ensure_empty_vritual_deps(self) -> None:
        written: list[tuple[protocols.ImportPath, str | None]] = []
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
        )

        def write_empty_virtual_dep(
            *, module_import_path: protocols.ImportPath
        ) -> protocols.ImportPath | None:
            if module_import_path == ImportPath("E1"):
                # This doesn't happen cause ".models." not in the path
                raise RuntimeError("Shouldn't get this far")
            elif module_import_path == ImportPath("E1.models"):
                written.append((module_import_path, "end models"))
                return ImportPath("VE1.models")
            elif module_import_path == ImportPath("E1.models.things"):
                written.append((module_import_path, "inside models"))
                return ImportPath("VE1.models.things")
            else:
                written.append((module_import_path, None))
                return None

        final_report = virtual_dependencies.ReportCombiner(
            report_maker=virtual_dependencies.Report, reports=(report1, report2)
        ).combine(version="__version__", write_empty_virtual_dep=write_empty_virtual_dep)

        assert final_report.version == "__version__"
        expected = virtual_dependencies.Report(
            concrete_annotations={
                ImportPath("P1"): ImportPath("CP1"),
                ImportPath("C1"): ImportPath("CC1"),
                ImportPath("C2"): ImportPath("CC2"),
            },
            concrete_querysets={
                ImportPath("P1"): ImportPath("CP1QS"),
                ImportPath("C1"): ImportPath("CC1QS"),
                ImportPath("C2"): ImportPath("C2QS"),
            },
            report_import_path={
                ImportPath("M1"): ImportPath("VM1"),
                ImportPath("M2"): ImportPath("VM2"),
            },
        )
        assert final_report.report == expected

        assert written == []

        # Can get content, but doesn't pass our naming heuristic
        final_report.ensure_virtual_dependency(module_import_path=ImportPath("E1"))
        assert written == []
        assert final_report.report == expected

        # passes naming heuristic of ending in .models
        final_report.ensure_virtual_dependency(module_import_path=(e2 := ImportPath("E1.models")))
        assert written == [(e2, "end models")]
        assert final_report.report != expected
        expected.report_import_path[e2] = ImportPath("VE1.models")
        assert final_report.report == expected

        # passes naming heuristic of containing .models.
        final_report.ensure_virtual_dependency(
            module_import_path=(e3 := ImportPath("E1.models.things"))
        )
        assert written == [(e2, "end models"), (e3, "inside models")]
        assert final_report.report != expected
        expected.report_import_path[e3] = ImportPath("VE1.models.things")
        assert final_report.report == expected

        # Passes heuristics but doesn't return a name
        final_report.ensure_virtual_dependency(
            module_import_path=(e4 := ImportPath("E2.models.ignoreme"))
        )
        assert written == [(e2, "end models"), (e3, "inside models"), (e4, None)]
        assert final_report.report == expected


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
        )

    @pytest.mark.parametrize("using_incremental_cache", (True, False))
    def test_additional_deps(self, using_incremental_cache: bool) -> None:
        report = virtual_dependencies.Report(
            report_import_path={
                ImportPath(k): ImportPath(v)
                for k, v in {
                    "one.two": "v_one_two",
                    "three.four": "v_three_four",
                    "five.six": "v_five_six",
                    "six.seven": "v_six_seven",
                    "eight.nine": "v_eight_nine",
                    "twelve.thirteen": "v_twelve_thirteen",
                    "another.one": "v_another_one",
                    "more": "v_more",
                }.items()
            }
        )

        ##
        ## These are the test cases above but they still only return super_deps

        # File name startswith django., it is effectively ignored
        made = report.additional_deps(
            file_import_path="django.db.models",
            imports=set(),
            super_deps=(super_deps := [(25, "one.two", -1), (25, "two", -1)]),
            django_settings_module="my.settings",
            using_incremental_cache=using_incremental_cache,
        )
        assert sorted(made) == sorted(super_deps)

        # Expansion depending only on super deps and imports
        made = report.additional_deps(
            file_import_path="some.place",
            imports=set(),
            super_deps=(super_deps := []),
            django_settings_module="my.settings",
            using_incremental_cache=using_incremental_cache,
        )
        assert sorted(made) == sorted(super_deps)

        made = report.additional_deps(
            file_import_path="some.place",
            imports={"eight.nine", "typing.Protocol"},
            super_deps=(super_deps := []),
            django_settings_module="my.settings",
            using_incremental_cache=using_incremental_cache,
        )
        assert sorted(made) == sorted(super_deps)

        made = report.additional_deps(
            file_import_path="some.place",
            imports=set(),
            super_deps=(super_deps := [(25, "eight.nine", -1), (25, "typing.Protocol", 13)]),
            django_settings_module="my.settings",
            using_incremental_cache=using_incremental_cache,
        )
        assert sorted(made) == sorted(super_deps)

        made = report.additional_deps(
            file_import_path="some.place",
            imports={"one.two"},
            super_deps=(super_deps := [(25, "hello.there", -1), (25, "typing.Protocol", 13)]),
            django_settings_module="my.settings",
            using_incremental_cache=using_incremental_cache,
        )
        assert sorted(made) == sorted(super_deps)

        # Also add from the file import itself
        made = report.additional_deps(
            file_import_path="another.one",
            imports={"one.two"},
            super_deps=(super_deps := [(25, "hello.there", -1), (25, "typing.Protocol", 13)]),
            django_settings_module="my.settings",
            using_incremental_cache=using_incremental_cache,
        )
        if using_incremental_cache:
            assert sorted(made) == sorted(
                [*super_deps, (25, "v_another_one", -1), (25, "my.settings", -1)]
            )
        else:
            assert sorted(made) == sorted([*super_deps, (25, "v_another_one", -1)])

        made = report.additional_deps(
            file_import_path="another.one",
            imports={"one.two.MyModel"},
            super_deps=(super_deps := [(25, "hello.there", -1), (25, "typing.Protocol", 13)]),
            django_settings_module="my.settings",
            using_incremental_cache=using_incremental_cache,
        )
        if using_incremental_cache:
            assert sorted(made) == sorted(
                [*super_deps, (25, "v_another_one", -1), (25, "my.settings", -1)]
            )
        else:
            assert sorted(made) == sorted([*super_deps, (25, "v_another_one", -1)])

        # Also virtual_deps themselves don't add extra
        made = report.additional_deps(
            file_import_path="v_another_one",
            imports={"one.two.MyModel"},
            super_deps=(super_deps := [(25, "hello.there", -1), (25, "typing.Protocol", 13)]),
            django_settings_module="my.settings",
            using_incremental_cache=using_incremental_cache,
        )
        assert sorted(made) == sorted(super_deps)
