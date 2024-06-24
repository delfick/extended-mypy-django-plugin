#!/usr/bin/env python
"""
This is used by the Mypy plugin to determine if the Django project has changed in a
way that would require the Mypy Daemon to restart itself.

The django-stubs plugin this relies on loads Django to perform introspection, which means
when Django ORM models or Django settings change, that introspection may no longer be correct.

The nature of how Django relies on globals and caches means it's very difficult to reliably
reload Django in a process where Django has already been loaded, and so this logic must be
done in a separate process.

The script relies on replicating Mypy plugin discovery logic to find a plugin that is based
off `extended_mypy_django_plugin.plugin.PluginProvider` to find the `VirtualDependencyHandler`
object that will determine a "version" for the project. This number is written to a file that
is specified on the command line to communicate back to the existing Mypy daemon process whether
to consider Django as changed or not.
"""

import argparse
import importlib
import os
import pathlib
import re
import sys

from extended_mypy_django_plugin.plugin import ExtraOptions, PluginProvider, protocols


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-file", help="The path to the mypy config file")
    parser.add_argument("--mypy-plugin", action="append", help="The mypy plugins configured")
    parser.add_argument(
        "--version-file", help="File to write the version to", type=pathlib.Path, required=True
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = make_parser()
    args = parser.parse_args(argv)

    # We need to know where the scratch path is so that we can find the special
    # file that tells us to pretend Django hasn't changed
    extra_options = ExtraOptions.from_config(args.config_file)

    if (extra_options.scratch_path / "__assume_django_state_unchanged__").exists():
        # An exit code of 2 tells the existing process to say the version hasn't changed
        sys.exit(2)

    plugin_provider: PluginProvider[protocols.Report] | None = None

    for plugin in args.mypy_plugin:
        found = load_plugin(plugin, args.config_file)
        if isinstance(found, PluginProvider):
            plugin_provider = found
            break

    if plugin_provider is None:
        raise ValueError("Couldn't find the extension that provides extended_mypy_django_plugin")

    report = plugin_provider.plugin_cls.make_virtual_dependency_report(
        extra_options=extra_options,
        virtual_dependency_handler=plugin_provider.virtual_dependency_handler,
    )

    # Communicate back the version we have. This is done explicitly rather than
    # by relying on filtering stdout or stderr
    args.version_file.write_text(report.version)


def load_plugin(plugin_path: str, config_file: str) -> object | None:
    """
    This is heavily based off what mypy itself does to load plugins
    """
    func_name = "plugin"
    plugin_dir: str | None = None
    if ":" in os.path.basename(plugin_path):
        plugin_path, func_name = plugin_path.rsplit(":", 1)

    if plugin_path.endswith(".py"):
        # Plugin paths can be relative to the config file location.
        plugin_path = os.path.join(os.path.dirname(config_file), plugin_path)
        if not os.path.isfile(plugin_path):
            return None

        plugin_dir = os.path.abspath(os.path.dirname(plugin_path))
        fnam = os.path.basename(plugin_path)
        module_name = fnam[:-3]
        sys.path.insert(0, plugin_dir)
    elif re.search(r"[\\/]", plugin_path):
        # Plugin does not have a .py extension
        return None
    else:
        module_name = plugin_path

    try:
        module = importlib.import_module(module_name)
    except Exception:
        return None
    finally:
        if plugin_dir is not None:
            assert sys.path[0] == plugin_dir
            del sys.path[0]

    if not hasattr(module, func_name):
        return None

    return getattr(module, func_name, None)


if __name__ == "__main__":
    main()
