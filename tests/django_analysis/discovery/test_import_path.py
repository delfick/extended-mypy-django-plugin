import pytest

from extended_mypy_django_plugin.django_analysis import ImportPath, discovery, protocols
from extended_mypy_django_plugin.django_analysis.discovery.import_path import ImportPathHelper


class TestImportPathHelper:
    def test_an_instance_is_provided(self) -> None:
        assert isinstance(ImportPath, ImportPathHelper)

    def test_can_return_path_to_class(self) -> None:
        assert (
            ImportPath.from_cls(TestImportPathHelper)
            == "tests.django_analysis.discovery.test_import_path.TestImportPathHelper"
        )
        assert (
            ImportPath.from_cls(ImportPathHelper)
            == "extended_mypy_django_plugin.django_analysis.discovery.import_path.ImportPathHelper"
        )

    def test_can_return_module_import_path_from_class(self) -> None:
        assert (
            ImportPath.cls_module(TestImportPathHelper)
            == "tests.django_analysis.discovery.test_import_path"
        )
        assert (
            ImportPath.cls_module(ImportPathHelper)
            == "extended_mypy_django_plugin.django_analysis.discovery.import_path"
        )

    def test_can_split_an_import_path(self) -> None:
        assert ImportPath.split(protocols.ImportPath("somewhere.nice")) == (
            protocols.ImportPath("somewhere"),
            protocols.ImportPath("nice"),
        )
        assert ImportPath.split(protocols.ImportPath("somewhere.else.that.is.good")) == (
            protocols.ImportPath("somewhere.else.that.is"),
            protocols.ImportPath("good"),
        )

    def test_complains_if_splitting_non_namespaced_import(self) -> None:
        with pytest.raises(discovery.InvalidImportPath):
            ImportPath.split(protocols.ImportPath("not_namespaced"))

    def test_turns_string_into_import_path(self) -> None:
        assert ImportPath("hello.there") == protocols.ImportPath("hello.there")
        assert ImportPath("place") == protocols.ImportPath("place")

    @pytest.mark.parametrize(
        "invalid",
        (
            pytest.param(".wat", id="starts_with_dot"),
            pytest.param("stuff..things", id="double_dot"),
            pytest.param("3stuff", id="starts_with_number"),
            pytest.param("things-stuff", id="dashes_not_valid_identifier"),
            pytest.param("", id="empty_string"),
            pytest.param("%%%", id="another_invalid_identifier"),
        ),
    )
    def test_complains_if_string_is_not_valid_import_path(self, invalid: str) -> None:
        with pytest.raises(discovery.InvalidImportPath):
            ImportPath(invalid)
