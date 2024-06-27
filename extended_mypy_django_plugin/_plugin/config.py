import configparser
import dataclasses
import pathlib
import sys
from collections.abc import Mapping

from mypy_django_plugin import config as django_stubs_config
from typing_extensions import Self

from ..django_analysis import ImportPath, protocols
from ..version import VERSION

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


@dataclasses.dataclass(frozen=True)
class ExtraOptions:
    """
    The extended_mypy_django_plugin adds two options to the django-stubs configuration in the mypy configuration

    scratch_path
        A folder where virtual dependencies are written to

    project_root
        This defaults to the folder the config is found in. It should be the path to the root of
        the project. This value will be added to sys.path before Django is loaded

    django_settings_module
        The option used to set DJANGO_SETTINGS_MODULE when loading django
    """

    scratch_path: pathlib.Path
    project_root: pathlib.Path
    django_settings_module: protocols.ImportPath

    @classmethod
    def from_config(cls, filepath: str | pathlib.Path | None) -> Self:
        if filepath is None:
            django_stubs_config.exit_with_error(django_stubs_config.INVALID_FILE)

        config_path = pathlib.Path(filepath)
        return cls.from_options(options=_parse_mypy_config(config_path), filepath=config_path)

    @classmethod
    def from_options(cls, *, options: Mapping[str, object], filepath: pathlib.Path) -> Self:
        """
        Construct the extra options from the mypy configuration
        """
        scratch_path = _sanitize_path(filepath, options, "scratch_path", required=True)
        assert scratch_path is not None

        project_root = _sanitize_path(filepath, options, "project_root")
        if project_root is None:
            project_root = filepath.parent

        django_settings_module_value = _sanitize_str(
            filepath, options, "django_settings_module", required=True
        )
        assert django_settings_module_value is not None
        django_settings_module = ImportPath(django_settings_module_value)

        scratch_path.mkdir(parents=True, exist_ok=True)

        return cls(
            scratch_path=scratch_path,
            project_root=project_root,
            django_settings_module=django_settings_module,
        )

    def for_report(self) -> dict[str, str]:
        """
        Get the options that were found to be used for the mypy report_config_data hook
        """
        return {
            "scratch_path": str(self.scratch_path),
            "project_root": str(self.project_root),
            "django_settings_module": self.django_settings_module,
            "plugin_version": str(VERSION),
        }


def _parse_mypy_config(filepath: pathlib.Path) -> Mapping[str, object]:
    if filepath.suffix == ".toml":
        return _parse_toml_config(filepath)
    else:
        return _parse_ini_config(filepath)


def _parse_toml_config(filepath: pathlib.Path) -> Mapping[str, object]:
    try:
        with filepath.open(mode="rb") as f:
            data = tomllib.load(f)
    except (tomllib.TOMLDecodeError, OSError):
        django_stubs_config.exit_with_error(django_stubs_config.COULD_NOT_LOAD_FILE, is_toml=True)

    if not isinstance(tool := data.get("tool"), Mapping) or not isinstance(
        result := tool.get("django-stubs"), Mapping
    ):
        django_stubs_config.exit_with_error(
            django_stubs_config.MISSING_SECTION.format(section="tool.django-stubs"),
            is_toml=True,
        )

    return result


def _parse_ini_config(filepath: pathlib.Path) -> Mapping[str, object]:
    parser = configparser.ConfigParser()
    try:
        with filepath.open(encoding="utf-8") as f:
            parser.read_file(f, source=str(filepath))
    except (configparser.ParsingError, OSError):
        django_stubs_config.exit_with_error(django_stubs_config.COULD_NOT_LOAD_FILE)

    section = "mypy.plugins.django-stubs"
    if not parser.has_section(section):
        django_stubs_config.exit_with_error(
            django_stubs_config.MISSING_SECTION.format(section=section)
        )

    return dict(parser.items("mypy.plugins.django-stubs"))


def _sanitize_str(
    config_path: pathlib.Path,
    options: Mapping[str, object],
    option: str,
    *,
    required: bool = False,
) -> str | None:
    if not isinstance(value := options.get(option), str):
        if required:
            raise ValueError(
                f"Please specify '{option}' in the django-stubs section of your mypy configuration ({config_path})"
            )
        else:
            return None

    while value and value.startswith('"'):
        value = value[1:]
    while value and value.endswith('"'):
        value = value[:-1]

    return value


def _sanitize_path(
    config_path: pathlib.Path,
    options: Mapping[str, object],
    option: str,
    *,
    required: bool = False,
) -> pathlib.Path | None:
    value = _sanitize_str(config_path, options, option, required=required)
    if value is None:
        return None
    return pathlib.Path(value.replace("$MYPY_CONFIG_FILE_DIR", str(config_path.parent)))
