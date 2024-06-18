import pathlib
from typing import TYPE_CHECKING, TypeVar

from ..django_analysis import virtual_dependencies
from ..django_analysis.protocols import (
    VirtualDependencyHandler as VirtualDependencyHandlerProtocol,
)

Report = virtual_dependencies.Report
T_Report = TypeVar("T_Report", bound=Report)


class DefaultVirtualDependencyHandler:
    @classmethod
    def create(
        cls,
        *,
        project_root: pathlib.Path,
        django_settings_module: str,
        virtual_deps_destination: pathlib.Path,
    ) -> Report:
        return Report()


__all__ = [
    "VirtualDependencyHandlerProtocol",
    "DefaultVirtualDependencyHandler",
    "T_Report",
    "Report",
]

if TYPE_CHECKING:
    C_VirtualDependencyHandler = DefaultVirtualDependencyHandler

    _CDVDH: VirtualDependencyHandlerProtocol[virtual_dependencies.Report] = (
        C_VirtualDependencyHandler.create
    )
