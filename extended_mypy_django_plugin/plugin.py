import pathlib

from ._plugin._config import ExtraOptions
from ._plugin._entry import PluginProvider
from ._plugin._plugin import ExtendedMypyStubs
from ._plugin._virtual_dependencies import (
    CombinedReportProtocol,
    DefaultVirtualDependencyHandler,
    ReportProtocol,
    T_Report,
    VirtualDependencyHandlerProtocol,
)
from .django_analysis import Project, discovery, protocols


class VirtualDependencyHandler(DefaultVirtualDependencyHandler[Project]):
    @classmethod
    def discover_project(
        cls, *, project_root: pathlib.Path, django_settings_module: str
    ) -> protocols.Discovered[Project]:
        return (
            Project(
                root_dir=project_root,
                additional_sys_path=[str(project_root)],
                env_vars={"DJANGO_SETTINGS_MODULE": django_settings_module},
                discovery=discovery.Discovery(),
            )
            .load_project()
            .perform_discovery()
        )


__all__ = [
    "T_Report",
    "ExtraOptions",
    "PluginProvider",
    "ReportProtocol",
    "ExtendedMypyStubs",
    "CombinedReportProtocol",
    "VirtualDependencyHandler",
    "DefaultVirtualDependencyHandler",
    "VirtualDependencyHandlerProtocol",
]
