import pathlib
import subprocess
import sys
import tempfile
from collections.abc import MutableMapping
from itertools import chain
from typing import Generic

from mypy.options import Options
from mypy.plugin import Plugin as MypyPlugin

from . import plugin, protocols


class PluginProvider(Generic[protocols.T_Report]):
    """
    This can be used to provide both a mypy plugin as well as a __version__ that changes
    when mypy needs to do a full restart.

    Given either the extended_mypy_django_plugin.plugin.ExtendedMypyStubs class or a subclass
    of that, usage is::

        from extended_mypy_django_plugin.plugin import ExtendedMypyStubs, PluginProvider, VirtualDependencyHandler

        plugin = PluginProvider(ExtendedMypyStubs, VirtualDependencyHandler.create_report, locals())
    """

    previous_version: str

    def __init__(
        self,
        plugin_cls: type[plugin.ExtendedMypyStubs[protocols.T_Report]],
        virtual_dependency_handler: protocols.VirtualDependencyHandler[protocols.T_Report],
        locals: MutableMapping[str, object],
        /,
    ) -> None:
        self.locals = locals
        self.instance: plugin.ExtendedMypyStubs[protocols.T_Report] | None = None
        self.virtual_dependency_handler = virtual_dependency_handler
        self.plugin_cls = plugin_cls

    def __call__(self, version: str) -> type[MypyPlugin]:
        if self.instance is not None:
            # This only happens when using the mypy daemon
            # and also self.instance is only ever not None after previous_version is set
            # In this case if the options have changed then dmypy will already have restarted
            # So we can rely on the options on our previous instance
            self.set_new_version(
                self.determine_plugin_version(
                    options=self.instance.options, previous_version=self.previous_version
                )
            )

            # Inside dmypy, don't create a new plugin
            return MypyPlugin

        provider = self
        major, minor, _ = version.split(".", 2)

        def __init__(
            instance: plugin.ExtendedMypyStubs[protocols.T_Report], options: Options
        ) -> None:
            super(instance.__class__, instance).__init__(
                options,
                mypy_version_tuple=(int(major), int(minor)),  # type: ignore[call-arg]
                virtual_dependency_handler=self.virtual_dependency_handler,
            )
            provider.set_new_version(instance.virtual_dependency_report.version)
            provider.instance = instance

        return type("Plugin", (provider.plugin_cls,), {"__init__": __init__})

    def set_new_version(self, new_version: str) -> None:
        self.previous_version = new_version
        self.locals["__version__"] = new_version

    def determine_plugin_version(self, *, options: Options, previous_version: str) -> str:
        cmd = [
            sys.executable,
            "-m",
            "extended_mypy_django_plugin.scripts.determine_django_state",
            *(["--config-file", options.config_file] if options.config_file is not None else []),
            *chain.from_iterable(["--mypy-plugin", plugin] for plugin in options.plugins),
        ]

        err: subprocess.CalledProcessError | None = None

        with tempfile.NamedTemporaryFile() as fle:
            cmd.extend(["--version-file", fle.name])

            try:
                subprocess.run(cmd, capture_output=True, check=True)
            except subprocess.CalledProcessError as failed:
                err = failed
            else:
                return pathlib.Path(fle.name).read_text().strip()

        if err.returncode == 2:
            return previous_version
        else:
            message = [
                "",
                "Failed to determine information about the django setup",
                "",
                f"  > {' '.join(cmd)}",
                "  |",
            ]
            if err.stdout:
                for line in err.stdout.splitlines():
                    if isinstance(line, bytes):
                        line = line.decode()
                    message.append(f"  | {line}")
                if err.stderr:
                    message.append("  |")
            if err.stderr:
                for line in err.stderr.splitlines():
                    if isinstance(line, bytes):
                        line = line.decode()
                    message.append(f"  | {line}")
            message.append("  |")

            if previous_version:
                print("\n".join(message), file=sys.stderr)  # noqa: T201
                return previous_version
            else:
                raise RuntimeError("\n".join(message))
