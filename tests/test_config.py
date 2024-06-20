import pathlib
import textwrap

import pytest

from extended_mypy_django_plugin.django_analysis import ImportPath
from extended_mypy_django_plugin.plugin import ExtraOptions


class TestGetExtraOptions:
    def test_it_can_get_options_from_ini_file(self, tmp_path: pathlib.Path) -> None:
        config = tmp_path / "config.ini"

        config.write_text(
            textwrap.dedent("""
        [mypy.plugins.django-stubs]
        project_root = $MYPY_CONFIG_FILE_DIR/project
        scratch_path = $MYPY_CONFIG_FILE_DIR/.mypy_django_scratch/main
        django_settings_module = my.settings
        """)
        )

        expected_scratch = tmp_path / ".mypy_django_scratch" / "main"
        assert not expected_scratch.exists()

        assert ExtraOptions.from_config(config) == ExtraOptions(
            project_root=tmp_path / "project",
            django_settings_module=ImportPath("my.settings"),
            scratch_path=expected_scratch,
        )

        assert expected_scratch.exists()

    def test_it_can_get_options_from_toml_file(self, tmp_path: pathlib.Path) -> None:
        config = tmp_path / "pyproject.toml"

        config.write_text(
            textwrap.dedent("""
        [tool.django-stubs]
        project_root = "$MYPY_CONFIG_FILE_DIR/project"
        scratch_path = "$MYPY_CONFIG_FILE_DIR/.mypy_django_scratch/main"
        django_settings_module = "my.settings"
        """)
        )

        expected_scratch = tmp_path / ".mypy_django_scratch" / "main"
        assert not expected_scratch.exists()

        assert ExtraOptions.from_config(config) == ExtraOptions(
            project_root=tmp_path / "project",
            scratch_path=expected_scratch,
            django_settings_module=ImportPath("my.settings"),
        )

        assert expected_scratch.exists()

    def test_complains_if_django_settings_module_is_not_specified(
        self, tmp_path: pathlib.Path
    ) -> None:
        versions = (
            (
                "mypy.ini",
                """
                [mypy.plugins.django-stubs]
                scratch_path = $MYPY_CONFIG_FILE_DIR/.mypy_django_scratch/main
                """,
            ),
            (
                "pyproject.toml",
                """
                [tool.django-stubs]
                scratch_path = "$MYPY_CONFIG_FILE_DIR/.mypy_django_scratch/main"
                """,
            ),
        )

        for name, content in versions:
            config = tmp_path / name
            config.write_text(textwrap.dedent(content))

            with pytest.raises(
                ValueError,
                match="Please specify 'django_settings_module' in the django-stubs section of your mypy configuration",
            ):
                ExtraOptions.from_config(config)

    def test_complains_if_django_settings_module_is_not_valid(
        self, tmp_path: pathlib.Path
    ) -> None:
        versions = (
            (
                "mypy.ini",
                """
                [mypy.plugins.django-stubs]
                scratch_path = $MYPY_CONFIG_FILE_DIR/.mypy_django_scratch/main
                django_settings_module = -asdf
                """,
            ),
            (
                "pyproject.toml",
                """
                [tool.django-stubs]
                scratch_path = "$MYPY_CONFIG_FILE_DIR/.mypy_django_scratch/main"
                django_settings_module = "-asdf"
                """,
            ),
        )

        for name, content in versions:
            config = tmp_path / name
            config.write_text(textwrap.dedent(content))

            with pytest.raises(
                ValueError,
                match="Provided path was not a valid python import path: '-asdf'",
            ):
                ExtraOptions.from_config(config)

    def test_complains_if_scratch_path_not_specified(self, tmp_path: pathlib.Path) -> None:
        versions = (
            (
                "mypy.ini",
                """
                [mypy.plugins.django-stubs]
                django_settings_module = my.settings
                """,
            ),
            (
                "pyproject.toml",
                """
                [tool.django-stubs]
                django_settings_module = "my.settings"
                """,
            ),
        )

        for name, content in versions:
            config = tmp_path / name
            config.write_text(textwrap.dedent(content))

            with pytest.raises(
                ValueError,
                match="Please specify 'scratch_path' in the django-stubs section of your mypy configuration",
            ):
                ExtraOptions.from_config(config)

    def test_complains_if_config_file_is_none(self) -> None:
        with pytest.raises(SystemExit):
            ExtraOptions.from_config(None)

    def test_complains_if_config_file_is_invalid_format(self, tmp_path: pathlib.Path) -> None:
        versions = (
            (
                "mypy.ini",
                """
                [mypy.plugins.django-stubs
                scratch_path = $MYPY_CONFIG_FILE_DIR/.mypy_django_scratch/main
                django_settings_module = my.settings
                """,
            ),
            (
                "pyproject.toml",
                """
                [tool.django-stubs
                scratch_path = "$MYPY_CONFIG_FILE_DIR/.mypy_django_scratch/main"
                django_settings_module = "my.settings"
                """,
            ),
        )

        for name, content in versions:
            config = tmp_path / name
            config.write_text(textwrap.dedent(content))

            with pytest.raises(SystemExit):
                ExtraOptions.from_config(config)

    def test_complains_if_config_file_is_missing_django_stubs_section(
        self, tmp_path: pathlib.Path
    ) -> None:
        versions = (
            (
                "mypy.ini",
                """
                [mypy.plugins.not-correct]
                hello = there
                django_settings_module = my.settings
                """,
            ),
            (
                "pyproject.toml",
                """
                [tool.not-correct]
                hello = "there"
                django_settings_module = "my.settings"
                """,
            ),
        )

        for name, content in versions:
            config = tmp_path / name
            config.write_text(textwrap.dedent(content))

            with pytest.raises(SystemExit):
                ExtraOptions.from_config(config)
