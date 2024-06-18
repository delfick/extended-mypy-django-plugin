import pathlib

from .django_analysis import Project, discovery, protocols
from .entry import PluginProvider
from .plugin import DefaultVirtualDependencyHandler, ExtendedMypyStubs


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


plugin = PluginProvider(ExtendedMypyStubs, VirtualDependencyHandler.create_report, locals())
