import enum
from collections.abc import Iterator, Mapping, MutableMapping, Sequence, Set
from typing import TYPE_CHECKING, Optional, Protocol, TypeVar

from mypy import errorcodes
from mypy.nodes import SymbolTableNode, TypeInfo
from mypy.plugin import (
    AnalyzeTypeContext,
    AttributeContext,
    DynamicClassDefContext,
    FunctionContext,
    MethodContext,
)
from mypy.types import (
    AnyType,
    Instance,
    PlaceholderType,
    ProperType,
    TypeType,
    TypeVarType,
    UnionType,
)
from mypy.types import Type as MypyType

from ..django_analysis import protocols as d_protocols

T_Report = TypeVar("T_Report", bound="Report")


CombinedReport = d_protocols.CombinedReport
VirtualDependencyHandler = d_protocols.VirtualDependencyHandler

TypeVarMap = MutableMapping[TypeVarType, Instance | TypeType | UnionType]


class KnownClasses(enum.Enum):
    CONCRETE = "extended_mypy_django_plugin.annotations.Concrete"


class KnownAnnotations(enum.Enum):
    CONCRETE = "extended_mypy_django_plugin.annotations.Concrete"
    DEFAULT_QUERYSET = "extended_mypy_django_plugin.annotations.DefaultQuerySet"

    @classmethod
    def resolve(cls, fullname: str) -> Optional["KnownAnnotations"]:
        """
        This function is an alternative to a try..catch(ValueError) that is quicker
        """
        if fullname == cls.CONCRETE.value:
            return cls.CONCRETE

        elif fullname == cls.DEFAULT_QUERYSET.value:
            return cls.DEFAULT_QUERYSET

        else:
            return None


class Report(Protocol):
    def additional_deps(
        self,
        *,
        file_import_path: str,
        imports: Set[str],
        super_deps: Sequence[tuple[int, str, int]],
        django_settings_module: str,
        using_incremental_cache: bool,
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


class FailFunc(Protocol):
    """
    Used to insert an error into the mypy output
    """

    def __call__(self, msg: str, code: errorcodes.ErrorCode | None = None) -> None: ...


class DeferFunc(Protocol):
    """
    Used to tell mypy to defer and come back later

    Returns True if was able to defer
    """

    def __call__(self) -> bool: ...


class LookupInfo(Protocol):
    """
    Given some fullname return a TypeInfo if one can be found
    """

    def __call__(self, fullname: str) -> TypeInfo | None: ...


class NamedTypeOrNone(Protocol):
    """
    Given some fullname and arguments, find the type info for that fullname if can be found and
    return an instance representing that object with those arguments
    """

    def __call__(self, fullname: str, args: list[MypyType] | None = None) -> Instance | None: ...


class AliasGetter(Protocol):
    """
    Given fullnames to zero or more models return a Mapping of those models to type aliases
    for the concrete aliases of that model where the value in the mapping is None if the alias
    could not be found.
    """

    def __call__(self, *models: str) -> Mapping[str, str | None]: ...


class LookupAlias(Protocol):
    """
    Given an alias for the concrete of some model, return Instance of the models represented
    by that type alias
    """

    def __call__(self, alias: str) -> Iterator[Instance | PlaceholderType]: ...


class LookupFullyQualified(Protocol):
    """
    Find a symbol for the provided fullname
    """

    def __call__(self, fullname: str) -> SymbolTableNode | None: ...


class ResolveManagerMethodFromInstance(Protocol):
    """
    Used to fold the fix from https://github.com/typeddjango/django-stubs/pull/2027 into the plugin
    """

    def __call__(
        self, instance: Instance, method_name: str, ctx: AttributeContext
    ) -> MypyType: ...


class Resolver(Protocol):
    """
    Used to resolve concrete annotations
    """

    def resolve(
        self, annotation: KnownAnnotations, model_type: ProperType
    ) -> Instance | TypeType | UnionType | AnyType | PlaceholderType | None:
        """
        Given a specific annotation and some model return the resolved
        concrete form.
        """


ValidContextForAnnotationResolver = (
    DynamicClassDefContext
    | AnalyzeTypeContext
    | AttributeContext
    | MethodContext
    | FunctionContext
)


class ResolverMaker(Protocol):
    """
    This is used to create an instance of Resolver
    """

    def __call__(cls, *, ctx: ValidContextForAnnotationResolver) -> Resolver: ...


class SignatureInfo(Protocol):
    """
    This is used by the type checker to represent important information about a signature for
    a method or function
    """

    @property
    def is_guard(self) -> bool:
        """
        Whether this signature represents a type guard
        """

    @property
    def transformed_ret_type(self) -> ProperType:
        """
        The return type of the signature after resolving annotations
        """


if TYPE_CHECKING:
    P_Report = Report
    P_Resolver = Resolver
    P_ResolverMaker = ResolverMaker
    P_VirtualDependencyHandler = VirtualDependencyHandler[P_Report]
