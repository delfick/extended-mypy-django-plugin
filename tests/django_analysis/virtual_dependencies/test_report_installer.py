import os
import pathlib

import pytest

from extended_mypy_django_plugin.django_analysis import ImportPath, protocols, virtual_dependencies


class TestReportInstaller:
    class TestWriteReport:
        def test_can_write_to_the_virtual_import_path(self, tmp_path: pathlib.Path) -> None:
            installer = virtual_dependencies.ReportInstaller(_get_report_summary=lambda path: None)
            assert installer._written == {}

            content = "hello\nthere"
            content2 = "things\nstuff\n"
            content3 = "compelling\nexample\n"

            scratch_root = tmp_path
            assert list(tmp_path.iterdir()) == []

            installer.write_report(
                scratch_root=scratch_root,
                summary_hash="__summary__",
                virtual_import_path=ImportPath("mod_blah"),
                content=content,
            )

            assert len(list(tmp_path.iterdir())) == 1
            location = tmp_path / "mod_blah.py"
            assert location.exists()
            assert location.read_text() == content
            assert installer._written == {location: "__summary__"}

            # With folders
            installer.write_report(
                scratch_root=scratch_root,
                summary_hash="__summary2__",
                virtual_import_path=ImportPath("forest.of.trees"),
                content=content2,
            )

            found: list[pathlib.Path] = []
            for root, _, files in os.walk(scratch_root):
                for name in files:
                    found.append(pathlib.Path(root) / name)

            location2 = scratch_root / "forest" / "of" / "trees.py"
            assert found == [location, location2]
            assert location.read_text() == content
            assert location2.read_text() == content2

            assert installer._written == {location: "__summary__", location2: "__summary2__"}

            # And with None summary hash
            installer.write_report(
                scratch_root=scratch_root,
                summary_hash=None,
                virtual_import_path=ImportPath("mod_other"),
                content=content3,
            )

            found = []
            for root, _, files in os.walk(scratch_root):
                for name in files:
                    found.append(pathlib.Path(root) / name)

            location3 = scratch_root / "mod_other.py"
            assert sorted(found) == sorted([location, location3, location2])
            assert location.read_text() == content
            assert location2.read_text() == content2
            assert location3.read_text() == content3

            assert installer._written == {
                location: "__summary__",
                location2: "__summary2__",
                location3: None,
            }

        @pytest.mark.parametrize(
            "bad_path",
            [
                pytest.param("/tmp/other", id="absolute_path"),
                pytest.param("../somewhere", id="relative_path"),
            ],
        )
        def test_complains_if_would_write_outside_scratch_folder(
            self, bad_path: str, tmp_path: pathlib.Path
        ) -> None:
            installer = virtual_dependencies.ReportInstaller(_get_report_summary=lambda path: None)
            assert installer._written == {}

            scratch_root = tmp_path

            with pytest.raises(
                RuntimeError, match="Virtual dependency ends up being outside of the scratch root"
            ):
                installer.write_report(
                    scratch_root=scratch_root,
                    summary_hash="__summary__",
                    virtual_import_path=protocols.ImportPath(bad_path),
                    content="stuff",
                )

    class TestInstallReports:
        def test_it_works_on_empty_folder(self, tmp_path_factory: pytest.TempPathFactory) -> None:
            scratch_root = tmp_path_factory.mktemp("scratch_root")
            destination_holder = tmp_path_factory.mktemp("destination")
            destination = destination_holder / "__virtual__"

            installer = virtual_dependencies.ReportInstaller(_get_report_summary=lambda path: None)
            installer.install_reports(
                scratch_root=scratch_root,
                destination=destination_holder,
                virtual_namespace=ImportPath("__virtual__"),
            )
            assert len(list(destination.iterdir())) == 0

        def test_it_copies_over_everything_that_was_written(
            self, tmp_path_factory: pytest.TempPathFactory
        ) -> None:
            scratch_root = tmp_path_factory.mktemp("scratch_root")
            destination_holder = tmp_path_factory.mktemp("destination")
            destination = destination_holder / "__virtual__"

            installer = virtual_dependencies.ReportInstaller(_get_report_summary=lambda path: None)

            installer.write_report(
                scratch_root=scratch_root,
                summary_hash="s1",
                virtual_import_path=ImportPath("__virtual__.mod_one"),
                content="1",
            )
            installer.write_report(
                scratch_root=scratch_root,
                summary_hash="s2",
                virtual_import_path=ImportPath("__virtual__.mod_two"),
                content="2",
            )
            installer.write_report(
                scratch_root=scratch_root,
                summary_hash="s3",
                virtual_import_path=ImportPath("__virtual__.mod_three"),
                content="3",
            )

            installer.install_reports(
                scratch_root=scratch_root,
                destination=destination_holder,
                virtual_namespace=ImportPath("__virtual__"),
            )
            assert len(list(destination.iterdir())) == 3

            assert (destination / "mod_one.py").read_text() == "1"
            assert (destination / "mod_two.py").read_text() == "2"
            assert (destination / "mod_three.py").read_text() == "3"

        def test_it_deletes_anything_that_gets_none_summary_and_wasnt_written(
            self, tmp_path_factory: pytest.TempPathFactory
        ) -> None:
            scratch_root = tmp_path_factory.mktemp("scratch_root")
            destination_holder = tmp_path_factory.mktemp("destination")
            destination = destination_holder / "__virtual__"
            destination.mkdir()

            (mod_one := destination / "mod_one.py").write_text("0")
            (mod_two := destination / "mod_two.py").write_text("existing")
            (mod_four := destination / "mod_four.py").write_text("4")
            (mod_five := destination / "mod_five.py").write_text("5")
            (some_dir := destination / "some_dir").mkdir()
            (destination / "some_dir" / "mod_thing.py").write_text("6")
            (destination / "some_dir" / "mod_seven.py").write_text("7")
            (destination / "some_dir" / "subdir").mkdir()
            (destination / "some_dir" / "subdir" / "mod_seven.py").write_text("7")
            nested = destination / "nested"
            hidden = destination / "hidden"
            (hidden / "down").mkdir(parents=True)
            (hidden / "down" / "here.py").write_text("for changing")

            report_summaries = {
                # mod one exists, return a different summary
                mod_one: "different",
                # mod two exists, return the same summary
                mod_two: "s2",
                # mod three doesn't exist, so not called, mod four not written to, has a summary, keep it
                mod_four: "keep",
                # Remove mod_five and everything under some_dir
                # we don't expect _get_report_summary to be called with anything under that directory
                mod_five: None,
                some_dir: None,
                # nested doesn't exist, we want it to not be deleted though
                nested: "_",
                nested / "mc": "_",
                # but hidden does exist and does get compared
                hidden: "_",
                hidden / "down": "_",
                hidden / "down" / "here.py": "_",
            }

            def _get_report_summary(location: pathlib.Path) -> str | None:
                return report_summaries.pop(location)

            installer = virtual_dependencies.ReportInstaller(
                _get_report_summary=_get_report_summary
            )

            installer.write_report(
                scratch_root=scratch_root,
                summary_hash="s1",
                virtual_import_path=ImportPath("__virtual__.mod_one"),
                content="1",
            )
            installer.write_report(
                scratch_root=scratch_root,
                summary_hash="s2",
                virtual_import_path=ImportPath("__virtual__.mod_two"),
                content="2",
            )
            installer.write_report(
                scratch_root=scratch_root,
                summary_hash="s3",
                virtual_import_path=ImportPath("__virtual__.mod_three"),
                content="3",
            )
            installer.write_report(
                scratch_root=scratch_root,
                summary_hash="__nested_hash__",
                virtual_import_path=ImportPath("__virtual__.nested.mc.nestface"),
                content="deep",
            )
            installer.write_report(
                scratch_root=scratch_root,
                summary_hash="__deep_hash__",
                virtual_import_path=ImportPath("__virtual__.hidden.down.here"),
                content="hiding",
            )

            installer.install_reports(
                scratch_root=scratch_root,
                destination=destination_holder,
                virtual_namespace=ImportPath("__virtual__"),
            )
            found: list[pathlib.Path] = []
            for root, _, files in os.walk(destination):
                for name in files:
                    found.append(pathlib.Path(root) / name)

            assert len(found) == 6

            # mod_one was changed
            assert mod_one.read_text() == "1"
            # two existed, had same summary, content doesn't change
            assert (destination / "mod_two.py").read_text() == "existing"
            # Three was added
            assert (destination / "mod_three.py").read_text() == "3"
            # four remained, the rest was deleted
            assert (destination / "mod_four.py").read_text() == "4"
            # our nested import was created with folders
            assert (destination / "nested" / "mc" / "nestface.py").read_text() == "deep"
            # our existing nested import was changed
            assert (destination / "hidden" / "down" / "here.py").read_text() == "hiding"

            # And _get_report_summary was called exactly as many times as our report_summaries had entries before
            assert report_summaries == {}
