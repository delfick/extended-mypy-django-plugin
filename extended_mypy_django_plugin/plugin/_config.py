import configparser
import dataclasses
import os
import pathlib
import sys
from collections.abc import Mapping

from typing_extensions import Self

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


@dataclasses.dataclass(frozen=True)
class ExtraOptions:
    """
    The extended_mypy_django_plugin adds two options to the django-stubs configuration in the mypy configuration

    This relies on django-stubs itself complaining before this point if the configuration isn't
    a valid configuration file before loading those options and finding the two additional options:

    scratch_path
        A folder where virtual dependencies are written to

    determine_django_state_script (optional)
        A script that can be run in a subprocess to determine the state of the django project.
        This is used when run in daemon mode to determine if the daemon needs to be restarted
    """

    scratch_path: pathlib.Path
    determine_django_state_script: pathlib.Path | None

    @classmethod
    def from_config(cls, filepath: pathlib.Path) -> Self:
        """
        Construct the extra options from the mypy configuration
        """
        options = _parse_mypy_config(filepath)

        scratch_path = _sanitize_path(filepath, options, "scratch_path", required=True)
        assert scratch_path is not None

        determine_django_state_script = _sanitize_path(
            filepath, options, "determine_django_state_script"
        )

        scratch_path.mkdir(parents=True, exist_ok=True)

        if determine_django_state_script is not None:
            error_prefix = f"The specified 'determine_django_state_script' option ({determine_django_state_script})"

            if not determine_django_state_script.exists():
                raise ValueError(f"{error_prefix} does not exist")

            if not determine_django_state_script.is_file():
                raise ValueError(f"{error_prefix} is not a file")

            if not os.access(determine_django_state_script, os.X_OK):
                raise ValueError(f"{error_prefix} is not executable")

        return cls(
            scratch_path=scratch_path, determine_django_state_script=determine_django_state_script
        )

    def for_report(self) -> dict[str, str]:
        """
        Get the options that were found to be used for the mypy report_config_data hook
        """
        return {
            "scratch_path": str(self.scratch_path),
            "determine_django_state_script": str(self.determine_django_state_script),
        }


def _parse_mypy_config(filepath: pathlib.Path) -> Mapping[str, object]:
    if filepath.suffix == ".toml":
        return _parse_toml_config(filepath)
    else:
        return _parse_ini_config(filepath)


def _parse_toml_config(filepath: pathlib.Path) -> Mapping[str, object]:
    # We know that ExtendedMypyStubs calls this code after we have a valid config
    # So I'm skipping error handling on loading the config file
    with filepath.open(mode="rb") as f:
        data = tomllib.load(f)

    result = data["tool"]["django-stubs"]
    if not isinstance(result, Mapping):
        raise ValueError("The tool.django-stubs section was not a dictionary")

    return result


def _parse_ini_config(filepath: pathlib.Path) -> Mapping[str, object]:
    # We know that ExtendedMypyStubs calls this code after we have a valid config
    # So I'm skipping error handling on loading the config file
    parser = configparser.ConfigParser()
    with filepath.open(encoding="utf-8") as f:
        parser.read_file(f, source=str(filepath))

    return dict(parser.items("mypy.plugins.django-stubs"))


def _sanitize_path(
    config_path: pathlib.Path,
    options: Mapping[str, object],
    option: str,
    *,
    required: bool = False,
) -> pathlib.Path | None:
    if not isinstance(value := options.get(option), str):
        if required:
            raise ValueError(
                f"Please specify '{option}' in the django-stubs section of your mypy configuration ({config_path}) as a string path"
            )
        else:
            return None

    while value and value.startswith('"'):
        value = value[1:]
    while value and value.endswith('"'):
        value = value[:-1]

    return pathlib.Path(value.replace("$MYPY_CONFIG_FILE_DIR", str(config_path.parent)))
