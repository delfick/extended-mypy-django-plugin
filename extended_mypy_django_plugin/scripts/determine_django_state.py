#!/usr/bin/env python

import argparse
import os
import pathlib
import sys
from collections.abc import Callable
from typing import TYPE_CHECKING

from extended_mypy_django_plugin import scripts

if TYPE_CHECKING:
    from django.apps.registry import Apps
    from django.conf import LazySettings


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--django-settings-module", help="The setting value to use for DJANGO_SETTINGS_MODULE"
    )
    parser.add_argument(
        "--apps-file",
        help="The file to print the installed apps to, one app per line",
        type=pathlib.Path,
    )
    parser.add_argument(
        "--known-models-file",
        help="The file to print the known models to",
        type=pathlib.Path,
    )
    parser.add_argument(
        "--known-settings-file",
        help="The file to print the known settings to",
        type=pathlib.Path,
    )
    parser.add_argument(
        "--scratch-path",
        help="The folder that the plugin is allowed to write in",
        type=pathlib.Path,
    )
    return parser


def main(
    argv: list[str] | None = None,
    additional_django_setup: Callable[[], None] | None = None,
    record_known_settings: Callable[[pathlib.Path, "LazySettings"], None] | None = None,
    record_known_models: Callable[[pathlib.Path, "Apps"], None] | None = None,
) -> None:
    parser = make_parser()
    args = parser.parse_args(argv)

    if (args.scratch_path / "__assume_django_state_unchanged__").exists():
        sys.exit(2)

    os.environ["DJANGO_SETTINGS_MODULE"] = args.django_settings_module
    if additional_django_setup:
        additional_django_setup()

    # add current directory to sys.path
    sys.path.append(str(pathlib.Path.cwd()))

    from django.apps import apps
    from django.conf import settings

    if not settings.configured:
        settings._setup()  # type: ignore[misc]
    apps.populate(settings.INSTALLED_APPS)

    assert apps.apps_ready, "Apps are not ready"
    assert settings.configured, "Settings are not configured"

    args.apps_file.write_text("\n".join(settings.INSTALLED_APPS))
    if record_known_models is None:
        record_known_models = scripts.record_known_models
    record_known_models(args.known_models_file, apps)

    if record_known_settings is None:
        record_known_settings = scripts.record_known_settings
    record_known_settings(args.known_settings_file, settings)


if __name__ == "__main__":
    main()
