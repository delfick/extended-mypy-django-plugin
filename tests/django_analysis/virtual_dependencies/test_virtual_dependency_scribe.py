import importlib
import pathlib
import shutil

import pytest

from extended_mypy_django_plugin.django_analysis import virtual_dependencies

ReportSummaryGetter = virtual_dependencies.ReportSummaryGetter


class TestVirtualDependencyScribe:
    class TestGetSummary:
        @pytest.fixture
        def get_report_summary(self) -> ReportSummaryGetter:
            return virtual_dependencies.VirtualDependencyScribe.get_report_summary

        def test_it_says_no_to_directories(
            self, tmp_path: pathlib.Path, get_report_summary: ReportSummaryGetter
        ) -> None:
            assert get_report_summary(tmp_path) is None

        def test_it_says_no_if_the_path_doesnt_end_in_python_extension(
            self, tmp_path: pathlib.Path, get_report_summary: ReportSummaryGetter
        ) -> None:
            (without_extension := tmp_path / "one").write_text(
                'mod = "extended_mypy_django_plugin.version"\nsummary = "stuff"'
            )

            assert get_report_summary(without_extension) is None

            with_extension = tmp_path / "one.py"
            shutil.move(without_extension, with_extension)

            assert get_report_summary(with_extension) == "stuff"

        def test_it_says_yes_to_files_and_links(
            self, tmp_path: pathlib.Path, get_report_summary: ReportSummaryGetter
        ) -> None:
            (one := tmp_path / "one.py").write_text(
                'mod = "extended_mypy_django_plugin.version"\nsummary = "trees"'
            )
            (two := tmp_path / "two.py").symlink_to(one)

            assert get_report_summary(one) == "trees"
            assert get_report_summary(two) == "trees"

        def test_it_says_no_if_cant_find_mod(
            self, tmp_path: pathlib.Path, get_report_summary: ReportSummaryGetter
        ) -> None:
            (location := tmp_path / "one.py").write_text('summary = "things"')
            assert get_report_summary(location) is None

            with open(location, "a") as fle:
                fle.write('\nmod = "extended_mypy_django_plugin.version"')

            assert get_report_summary(location) == "things"

        def test_it_says_no_if_cant_find_summary(
            self, tmp_path: pathlib.Path, get_report_summary: ReportSummaryGetter
        ) -> None:
            (location := tmp_path / "one.py").write_text(
                'mod = "extended_mypy_django_plugin.version"'
            )
            assert get_report_summary(location) is None

            with open(location, "a") as fle:
                fle.write('\nsummary = "blah"')

            assert get_report_summary(location) == "blah"

        def test_it_says_no_if_cant_import_mod(
            self, tmp_path: pathlib.Path, get_report_summary: ReportSummaryGetter
        ) -> None:
            with pytest.raises(ModuleNotFoundError):
                importlib.import_module("does.not.exist")

            (location := tmp_path / "one.py").write_text(
                'mod = "does.not.exist\nsummary = "lalalala"'
            )
            assert get_report_summary(location) is None

            location.write_text('mod = "pytest"\nsummary = "ladelala"')
            assert get_report_summary(location) == "ladelala"
