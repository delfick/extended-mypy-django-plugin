import enum
import functools
from collections.abc import Callable
from typing import Generic, TypeVar

from mypy.nodes import (
    Import,
    ImportAll,
    ImportFrom,
    MypyFile,
    SymbolNode,
    SymbolTableNode,
    TypeInfo,
)
from mypy.options import Options
from mypy.plugin import (
    AnalyzeTypeContext,
    AttributeContext,
    DynamicClassDefContext,
    FunctionContext,
    FunctionSigContext,
    MethodContext,
    MethodSigContext,
    ReportConfigContext,
)
from mypy.types import FunctionLike
from mypy.types import Type as MypyType
from mypy_django_plugin import main
from mypy_django_plugin.transformers.managers import (
    resolve_manager_method,
    resolve_manager_method_from_instance,
)
from typing_extensions import assert_never

from . import actions, config, hook, protocols

# Can't re-use the same type var in an embedded class
# So we make another type var that we can substitute T_Report into
T_Report = TypeVar("T_Report", bound=protocols.Report)
T2_Report = TypeVar("T2_Report", bound=protocols.Report)


class Hook(
    Generic[T_Report, hook.T_Ctx, hook.T_Ret],
    hook.Hook["ExtendedMypyStubs[T_Report]", hook.T_Ctx, hook.T_Ret],
):
    pass


class ExtendedMypyStubs(Generic[T_Report], main.NewSemanalDjangoPlugin):
    """
    The ``ExtendedMypyStubs`` mypy plugin extends the
    ``mypy_django_plugin.main.NewSemanalDjangoPlugin`` found in the active python
    environment.

    It implements the following mypy plugin hooks:

    .. automethod:: get_additional_deps

    .. autoattribute:: get_dynamic_class_hook

    .. autoattribute:: get_type_analyze_hook

    .. autoattribute:: get_function_hook

    .. autoattribute:: get_attribute_hook
    """

    @classmethod
    def make_virtual_dependency_report(
        cls,
        *,
        extra_options: config.ExtraOptions,
        virtual_dependency_handler: protocols.VirtualDependencyHandler[protocols.T_Report],
    ) -> protocols.CombinedReport[protocols.T_Report]:
        return virtual_dependency_handler(
            project_root=extra_options.project_root,
            django_settings_module=extra_options.django_settings_module,
            virtual_deps_destination=extra_options.scratch_path,
        )

    def __init__(
        self,
        options: Options,
        mypy_version_tuple: tuple[int, int],
        virtual_dependency_handler: protocols.VirtualDependencyHandler[T_Report],
    ) -> None:
        self.options = options
        self.extra_options = config.ExtraOptions.from_config(options.config_file)
        self.mypy_version_tuple = mypy_version_tuple

        self.virtual_dependency_report = self.make_virtual_dependency_report(
            extra_options=self.extra_options, virtual_dependency_handler=virtual_dependency_handler
        )

        super().__init__(options)

    def _make_resolver(
        self, ctx: protocols.ValidContextForAnnotationResolver
    ) -> protocols.Resolver:
        return actions.make_resolver(
            get_concrete_aliases=self.virtual_dependency_report.report.get_concrete_aliases,
            get_queryset_aliases=self.virtual_dependency_report.report.get_queryset_aliases,
            plugin_lookup_info=self._lookup_info,
            plugin_lookup_fully_qualified=self.lookup_fully_qualified,
            ctx=ctx,
        )

    def _lookup_info(self, fullname: str) -> TypeInfo | None:
        sym = self.lookup_fully_qualified(fullname)
        if sym and isinstance(sym.node, TypeInfo):
            return sym.node
        else:
            return None

    def _get_symbolnode_for_fullname(
        self, fullname: str, is_function: bool
    ) -> SymbolNode | SymbolTableNode | None:
        sym = self.lookup_fully_qualified(fullname)
        if sym and sym.node:
            return sym.node

        if is_function:
            return None

        if fullname.count(".") < 2:
            return None

        if self._modules is None:
            return None

        # We're on a class and couldn't find the sym, it's likely on a base class
        module, class_name, method_name = fullname.rsplit(".", 2)

        mod = self._modules.get(module)
        if mod is None:
            return None

        class_node = mod.names.get(class_name)
        if not class_node or not isinstance(class_node.node, TypeInfo):
            return None

        for parent in class_node.node.bases:
            if isinstance(parent.type, TypeInfo):
                if isinstance(found := parent.type.names.get(method_name), SymbolTableNode):
                    return found

        return None

    def report_config_data(self, ctx: ReportConfigContext) -> dict[str, object]:
        """
        Add our extra options to the report config data, so that mypy knows to clear the cache
        if those settings change.
        """
        return {
            **super().report_config_data(ctx),
            "extended_mypy_django_plugin": self.extra_options.for_report(),
        }

    def get_additional_deps(self, file: MypyFile) -> list[tuple[int, str, int]]:
        """
        Ensure that models are re-analyzed if any other models that depend on
        them change.

        We use a generated "report" to re-analyze a file if a new dependency
        is discovered after this file has been processed.
        """
        file_import = file.fullname
        full_imports: set[str] = set()

        self.virtual_dependency_report.ensure_virtual_dependency(module_import_path=file.fullname)

        for imp in file.imports:
            if isinstance(imp, ImportFrom | ImportAll):
                if imp.relative:
                    prefix_base = ".".join(file_import.split(".")[: -imp.relative])
                    prefix = f"{prefix_base}.{imp.id}"
                else:
                    prefix = imp.id

                if isinstance(imp, ImportAll):
                    # This is the best we can do unfortunately
                    full_imports.add(prefix)
                else:
                    for name, _ in imp.names:
                        full_imports.add(f"{prefix}.{name}")

            elif isinstance(imp, Import):
                for name, _ in imp.ids:
                    full_imports.add(name)

        return list(
            self.virtual_dependency_report.report.additional_deps(
                file_import_path=file_import,
                imports=full_imports,
                django_settings_module=self.extra_options.django_settings_module,
                super_deps=super().get_additional_deps(file),
            )
        )

    @hook.hook
    class get_dynamic_class_hook(Hook[T_Report, DynamicClassDefContext, None]):
        """
        This is used to find special methods on the ``Concrete`` class and do appropriate actions.

        For ``Concrete.type_var`` we turn the result into a ``TypeVar`` that can only be one of
        the concrete descendants of the specified class.

        So say we find::

            T_Child = Concrete.type_var("T_Child", Parent)

        Then we turn that into::

            T_Child = TypeVar("T_Child", Child1, Child2, Child3)

        For ``Concrete.cast_as_concrete`` we narrow the target variable to be the concrete equivalent
        of the argument.
        """

        class KnownConcreteMethods(enum.Enum):
            type_var = "type_var"
            cast_as_concrete = "cast_as_concrete"

        method_name: KnownConcreteMethods

        def choose(self) -> bool:
            class_name, _, method_name = self.fullname.rpartition(".")
            try:
                self.method_name = self.KnownConcreteMethods(method_name)
            except ValueError:
                return False
            else:
                info = self.plugin._get_typeinfo_or_none(class_name)
                return bool(info and info.has_base(protocols.KnownClasses.CONCRETE.value))

        def run(self, ctx: DynamicClassDefContext) -> None:
            sem_analyzing = actions.SemAnalyzing(
                resolver=self.plugin._make_resolver(ctx), api=ctx.api
            )

            if self.method_name is self.KnownConcreteMethods.type_var:
                return sem_analyzing.transform_type_var_classmethod(ctx)
            elif self.method_name is self.KnownConcreteMethods.cast_as_concrete:
                return sem_analyzing.transform_cast_as_concrete(ctx)
            else:
                assert_never(self.method_name)

    @hook.hook
    class get_type_analyze_hook(Hook[T_Report, AnalyzeTypeContext, MypyType]):
        """
        Resolve classes annotated with ``Concrete`` or ``DefaultQuerySet``.
        """

        annotation: protocols.KnownAnnotations

        def choose(self) -> bool:
            try:
                self.annotation = protocols.KnownAnnotations(self.fullname)
            except ValueError:
                return False
            else:
                return True

        def run(self, ctx: AnalyzeTypeContext) -> MypyType:
            type_analyzer = actions.TypeAnalyzer(
                resolver=self.plugin._make_resolver(ctx), api=ctx.api
            )
            return type_analyzer.analyze(ctx, self.annotation)

    @hook.hook
    class get_attribute_hook(Hook[T_Report, AttributeContext, MypyType]):
        """
        An implementation of the change found in
        https://github.com/typeddjango/django-stubs/pull/2027
        """

        def choose(self) -> bool:
            return self.super_hook is resolve_manager_method

        def run(self, ctx: AttributeContext) -> MypyType:
            type_checking = actions.TypeChecking(
                resolver=self.plugin._make_resolver(ctx), api=ctx.api
            )

            return type_checking.extended_get_attribute_resolve_manager_method(
                ctx, resolve_manager_method_from_instance=resolve_manager_method_from_instance
            )

    class _get_method_or_function_hook(
        Generic[T2_Report], Hook[T2_Report, MethodContext | FunctionContext, MypyType]
    ):
        runner: Callable[[MethodContext | FunctionContext], MypyType | None]

        def extra_init(self) -> None:
            super().extra_init()
            self.shared_logic = actions.SharedModifyReturnTypeLogic(
                make_resolver=lambda ctx: self.plugin._make_resolver(ctx),
                fullname=self.fullname,
                get_symbolnode_for_fullname=functools.partial(
                    self.plugin._get_symbolnode_for_fullname,
                    is_function=self.__class__.__name__ == "get_function_hook",
                ),
            )

        def choose(self) -> bool:
            if self.shared_logic.choose():
                self.runner = self.shared_logic.run
                return True
            else:
                return False

        def run(self, ctx: FunctionContext | MethodContext) -> MypyType:
            result = self.runner(ctx)
            if result is not None:
                return result

            if self.super_hook is not None:
                return self.super_hook(ctx)

            return ctx.default_return_type

    @hook.hook
    class get_method_hook(_get_method_or_function_hook[T_Report]):
        pass

    @hook.hook
    class get_function_hook(_get_method_or_function_hook[T_Report]):
        pass

    class _get_method_or_function_signature_hook(
        Generic[T2_Report], Hook[T2_Report, MethodSigContext | FunctionSigContext, FunctionLike]
    ):
        def extra_init(self) -> None:
            super().extra_init()
            self.shared_logic = actions.SharedCheckTypeGuardsLogic(
                make_resolver=lambda ctx: self.plugin._make_resolver(ctx),
                fullname=self.fullname,
                get_symbolnode_for_fullname=functools.partial(
                    self.plugin._get_symbolnode_for_fullname,
                    is_function=self.__class__.__name__ == "get_function_hook",
                ),
            )

        def choose(self) -> bool:
            return self.shared_logic.choose()

        def run(self, ctx: MethodSigContext | FunctionSigContext) -> FunctionLike:
            result = self.shared_logic.run(ctx)
            if result is not None:
                return result

            if self.super_hook is not None:
                return self.super_hook(ctx)

            return ctx.default_signature

    @hook.hook
    class get_method_signature_hook(_get_method_or_function_signature_hook[T_Report]):
        pass

    @hook.hook
    class get_function_signature_hook(_get_method_or_function_signature_hook[T_Report]):
        pass
