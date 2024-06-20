import enum
from collections.abc import Mapping, Sequence, Set
from typing import TYPE_CHECKING, Protocol, TypeVar

from ..django_analysis import protocols as d_protocols

T_Report = TypeVar("T_Report", bound="Report")


CombinedReport = d_protocols.CombinedReport
VirtualDependencyHandler = d_protocols.VirtualDependencyHandler


class KnownClasses(enum.Enum):
    CONCRETE = "extended_mypy_django_plugin.annotations.Concrete"


class KnownAnnotations(enum.Enum):
    CONCRETE = "extended_mypy_django_plugin.annotations.Concrete"
    DEFAULT_QUERYSET = "extended_mypy_django_plugin.annotations.DefaultQuerySet"


class Report(Protocol):
    def additional_deps(
        self,
        *,
        file_import_path: str,
        imports: Set[str],
        super_deps: Sequence[tuple[int, str, int]],
        django_settings_module: str,
    ) -> Sequence[tuple[int, str, int]]:
        """
        This is used to add to the result for the get_additional_deps mypy hook.

        It takes the import path for the file being looked at, any additional deps that have already
        been determined for the file, the imports the file contains as a list of full imports,
        and the import path of the django settings module.

        It must return the full set of additional deps the mypy plugin should use for this file
        """

    def get_concrete_aliases(self, *models: str) -> Mapping[str, str | None]:
        """
        Given import paths to some models, return a map of those models to a type alias
        with the concrete models for that model

        If concrete models cannot be found for a model it's entry will be given as None
        """

    def get_queryset_aliases(self, *models: str) -> Mapping[str, str | None]:
        """
        Given import paths to some models, return a map of those models to a type alias
        with the concrete querysets for that model

        If concrete querysets cannot be found for a model it's entry will be given as None
        """


if TYPE_CHECKING:
    P_Report = Report
    P_VirtualDependencyHandler = VirtualDependencyHandler[P_Report]
