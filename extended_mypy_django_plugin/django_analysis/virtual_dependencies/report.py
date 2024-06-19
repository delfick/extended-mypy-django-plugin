from __future__ import annotations

import collections
import dataclasses
import functools
import importlib
import os
import pathlib
import re
import shutil
import textwrap
from collections.abc import Iterator, MutableMapping, MutableSet, Sequence, Set
from typing import TYPE_CHECKING, Generic, Protocol, TypeVar, cast

from .. import protocols
from ..discovery import ImportPath
from . import dependency

T_Report = TypeVar("T_Report", bound="Report")

regexes = {
    "mod_decl": re.compile(r'^mod = "(?P<mod>[^"]+)"$'),
    "summary_decl": re.compile(r'^summary = "(?P<summary>[^"]+)"$'),
}


@dataclasses.dataclass(frozen=True, kw_only=True)
class CombinedReport(Generic[protocols.T_Report]):
    version: str
    report: protocols.T_Report


@dataclasses.dataclass(frozen=True, kw_only=True)
class Report:
    concrete_annotations: MutableMapping[protocols.ImportPath, protocols.ImportPath] = (
        dataclasses.field(default_factory=dict)
    )
    concrete_querysets: MutableMapping[protocols.ImportPath, protocols.ImportPath] = (
        dataclasses.field(default_factory=dict)
    )
    report_import_path: MutableMapping[protocols.ImportPath, protocols.ImportPath] = (
        dataclasses.field(default_factory=dict)
    )
    related_import_paths: MutableMapping[
        protocols.ImportPath, MutableSet[protocols.ImportPath]
    ] = dataclasses.field(default_factory=lambda: collections.defaultdict(set))

    def register_module(
        self,
        *,
        module_import_path: protocols.ImportPath,
        virtual_import_path: protocols.ImportPath,
    ) -> None:
        self.report_import_path[module_import_path] = virtual_import_path

    def register_model(
        self,
        *,
        model_import_path: protocols.ImportPath,
        virtual_import_path: protocols.ImportPath,
        concrete_name: str,
        concrete_queryset_name: str,
        concrete_models: Sequence[protocols.Model],
    ) -> None:
        module_import_path, name = ImportPath.split(model_import_path)

        self.concrete_annotations[model_import_path] = ImportPath(
            f"{virtual_import_path}.{concrete_name}"
        )
        self.concrete_querysets[model_import_path] = ImportPath(
            f"{virtual_import_path}.{concrete_queryset_name}"
        )

        for concrete in concrete_models:
            ns, _ = ImportPath.split(concrete.import_path)
            if ns != module_import_path:
                self.related_import_paths[module_import_path].add(ns)
                self.related_import_paths[ns].add(module_import_path)

            if concrete.default_custom_queryset:
                ns, _ = ImportPath.split(concrete.default_custom_queryset)
                if ns != module_import_path:
                    self.related_import_paths[module_import_path].add(ns)
                    self.related_import_paths[ns].add(module_import_path)

            for field in concrete.all_fields.values():
                if field.related_model:
                    ns, _ = ImportPath.split(field.related_model)
                    if ns != module_import_path:
                        self.related_import_paths[module_import_path].add(ns)
                        self.related_import_paths[ns].add(module_import_path)

            for mro in concrete.models_in_mro:
                ns, _ = ImportPath.split(mro)
                if ns != module_import_path:
                    self.related_import_paths[module_import_path].add(ns)
                    self.related_import_paths[ns].add(module_import_path)

    def additional_deps(
        self,
        *,
        file_import_path: str,
        imports: Set[str],
        super_deps: Sequence[tuple[int, str, int]],
    ) -> Sequence[tuple[int, str, int]]:
        if file_import_path.startswith("django."):
            # Don't add additional deps to django itself
            return super_deps

        report_names = set(self.report_import_path.values())
        if file_import_path in report_names:
            # Don't add additional deps to our virtual imports
            # if things they depend on change, then the virtual dep also changes already
            return super_deps

        deps = set(super_deps)
        final = set(deps)
        mods = {name for _, name, _ in deps}

        # We want to make sure that our deps include imports from known modules so that when we expand
        # In the next section, we take into account dependencies of the imports as well
        for full in imports:
            if full == file_import_path:
                continue

            if full in self.report_import_path:
                if full not in mods:
                    mods.add(full)
                    deps.add((10, full, -1))
                continue

            for mod in self.report_import_path:
                if full.startswith(f"{mod}."):
                    if mod not in mods:
                        mods.add(mod)
                        deps.add((10, mod, -1))
                    break

        # and take into account this file itself!
        if file_import_path not in mods:
            mods.add(file_import_path)
            deps.add((10, file_import_path, -1))

        # Keep expanding the deps until it doesn't add any more
        while self._expand_additional_deps(deps):
            pass

        # Only keep the virtual dependencies we added
        for _, added, _ in deps - final:
            if added in report_names:
                final.add((10, added, -1))

        return list(final)

    def _expand_additional_deps(self, deps: MutableSet[tuple[int, str, int]]) -> bool:
        changed: bool = False

        mods = {mod for _, mod, _ in deps}

        for _, mod_s, _ in list(deps):
            mod = protocols.ImportPath(mod_s)
            report_name = self.report_import_path.get(mod)
            if report_name and report_name not in mods:
                changed = True
                mods.add(report_name)
                deps.add((10, report_name, -1))
                if mod in self.related_import_paths:
                    for related in self.related_import_paths[mod]:
                        mods.add(related)
                        deps.add((10, related, -1))

        return changed


@dataclasses.dataclass(frozen=True, kw_only=True)
class WrittenVirtualDependency(Generic[protocols.T_Report]):
    content: str
    summary_hash: str | None
    report: protocols.T_Report
    virtual_import_path: protocols.ImportPath


@dataclasses.dataclass(frozen=True, kw_only=True)
class VirtualDependencyScribe(Generic[protocols.T_VirtualDependency, protocols.T_Report]):
    hasher: protocols.Hasher
    report_maker: protocols.ReportMaker[protocols.T_Report]
    virtual_dependency: protocols.T_VirtualDependency
    all_virtual_dependencies: protocols.VirtualDependencyMap[protocols.T_VirtualDependency]

    def write(self) -> WrittenVirtualDependency[protocols.T_Report]:
        report = self.report_maker()
        summary_hash = self._get_summary_hash()

        module_import_path = self.virtual_dependency.summary.module_import_path
        virtual_import_path = self.virtual_dependency.summary.virtual_import_path
        report.register_module(
            module_import_path=module_import_path, virtual_import_path=virtual_import_path
        )

        content = self._template_virtual_dependency(
            report=report, virtual_import_path=virtual_import_path, summary_hash=summary_hash
        )

        return WrittenVirtualDependency(
            content=content,
            summary_hash=summary_hash,
            report=report,
            virtual_import_path=virtual_import_path,
        )

    @classmethod
    def get_report_summary(cls, location: pathlib.Path) -> str | None:
        """
        Given some location return the summary from that location.

        If the report doesn't have a summary or is for a module that doesn't exist anymore then return None
        """
        if not location.is_file():
            return None

        if location.suffix != ".py":
            return None

        mod: str | None = None
        summary: str | None = None
        for line in location.read_text().splitlines():
            m = regexes["mod_decl"].match(line)
            if m:
                mod = m.groupdict()["mod"]

            m = regexes["summary_decl"].match(line)
            if m:
                summary = m.groupdict()["summary"]

            if mod and summary:
                break

        if mod is None or summary is None:
            return None

        try:
            importlib.util.find_spec(mod)
        except ModuleNotFoundError:
            return None
        else:
            return summary

    def _get_summary_hash(self) -> str | None:
        summary = self.virtual_dependency.summary
        summary_hash: str | None = None
        if summary.significant_info:
            significant = self.hasher(*(info.encode() for info in summary.significant_info))
            summary_hash = "::".join(
                [
                    f"{summary.virtual_import_path}",
                    str(summary.module_import_path),
                    f"installed_apps={summary.installed_apps_hash}",
                    f"significant={significant}",
                ]
            )

        return summary_hash

    def _template_virtual_dependency(
        self,
        *,
        report: protocols.T_Report,
        virtual_import_path: protocols.ImportPath,
        summary_hash: str | None,
    ) -> str:
        differentiator = self.virtual_dependency.interface_differentiator
        module_import_path = self.virtual_dependency.summary.module_import_path
        summary = "None" if summary_hash is None else f'"{summary_hash}"'
        content = textwrap.dedent(f"""
        from typing import TYPE_CHECKING

        def interface__{'empty__' if differentiator is None else differentiator}() -> None:
            return None

        mod = "{module_import_path}"
        summary = {summary}

        if TYPE_CHECKING:
        """)

        added_imports: set[protocols.ImportPath] = set()
        annotations: set[str] = set()

        for model, concrete in self.virtual_dependency.concrete_models.items():
            querysets: set[str] = set()

            added_imports.add(model)
            for conc in concrete:
                added_imports.add(conc.import_path)
                if conc.default_custom_queryset:
                    added_imports.add(conc.default_custom_queryset)
                    querysets.add(conc.default_custom_queryset)
                else:
                    added_imports.add(ImportPath("django.db.models.QuerySet"))
                    querysets.add(f"django.db.models.QuerySet[{conc.import_path}]")

            ns, name = ImportPath.split(model)
            concrete_name = f"Concrete__{name}"
            queryset_name = f"ConcreteQuerySet__{name}"

            if concrete:
                annotations.add(
                    f"{concrete_name} = {' | '.join(sorted(conc.import_path for conc in concrete))}"
                )
            if querysets:
                annotations.add(f"{queryset_name} = {' | '.join(sorted(querysets))}")

            report.register_model(
                model_import_path=model,
                virtual_import_path=virtual_import_path,
                concrete_queryset_name=queryset_name,
                concrete_name=concrete_name,
                concrete_models=concrete,
            )

        sorted_added_imported_modules = sorted(
            {".".join(imp.split(".")[:-1]) for imp in added_imports}
        )

        extra_lines = [
            *(f"    import {import_path}" for import_path in sorted_added_imported_modules),
            *(f"    {line}" for line in sorted(annotations)),
        ]

        if extra_lines:
            content = content + "\n".join(extra_lines)
        else:
            content = content[: -len("\n\nif TYPE_CHECKING:") + 1]

        return content.strip() + "\n"


@dataclasses.dataclass(frozen=True, kw_only=True)
class ReportCombiner(Generic[T_Report]):
    reports: Sequence[T_Report]
    report_maker: protocols.ReportMaker[T_Report]

    def combine(self, *, version: str) -> protocols.CombinedReport[T_Report]:
        final = self.report_maker()
        for report in self.reports:
            final.concrete_annotations.update(report.concrete_annotations)
            final.concrete_querysets.update(report.concrete_querysets)
            final.report_import_path.update(report.report_import_path)

            for path, related in report.related_import_paths.items():
                final.related_import_paths[path] |= related

        return CombinedReport(version=version, report=final)


class ReportSummaryGetter(Protocol):
    """
    Protocol for a callable that returns a summary from a path

    Where None is returned if the path isn't a valid virtual dependency

    And a string is the summary from that virtual dependency
    """

    def __call__(self, location: pathlib.Path, /) -> str | None: ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class ReportInstaller:
    _written: dict[pathlib.Path, str | None] = dataclasses.field(init=False, default_factory=dict)
    _get_report_summary: ReportSummaryGetter

    def write_report(
        self,
        *,
        scratch_root: pathlib.Path,
        summary_hash: str | None,
        virtual_import_path: protocols.ImportPath,
        content: str,
    ) -> None:
        location = scratch_root / f"{virtual_import_path.replace('.', os.sep)}.py"
        if not location.is_relative_to(scratch_root):
            raise RuntimeError(
                f"Virtual dependency ends up being outside of the scratch root: {virtual_import_path}"
            )
        location.parent.mkdir(parents=True, exist_ok=True)
        location.write_text(content)
        self._written[location] = summary_hash

    def install_reports(
        self,
        *,
        scratch_root: pathlib.Path,
        destination: pathlib.Path,
        virtual_namespace: protocols.ImportPath,
    ) -> None:
        virtual_destination = destination / virtual_namespace
        virtual_destination.mkdir(parents=True, exist_ok=True)

        seen: set[pathlib.Path] = set()
        for location, summary in self._written.items():
            relative_path = location.relative_to(scratch_root)
            destination_path = destination / relative_path

            seen.add(destination_path)
            found_summary: str | None = None
            if destination_path.exists():
                found_summary = self._get_report_summary(destination_path)

            if found_summary != summary:
                destination_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(location, destination_path)

        for root, dirs, files in os.walk(virtual_destination):
            for name in list(dirs):
                location = pathlib.Path(root) / name
                if location not in seen:
                    if self._get_report_summary(location) is None:
                        shutil.rmtree(location)
                        dirs.remove(name)

            for name in files:
                location = pathlib.Path(root) / name
                if location not in seen:
                    if self._get_report_summary(location) is None:
                        location.unlink()


@dataclasses.dataclass(frozen=True, kw_only=True)
class ReportFactory(Generic[protocols.T_VirtualDependency, protocols.T_Report]):
    hasher: protocols.Hasher

    report_installer: protocols.ReportInstaller
    report_combiner_maker: protocols.ReportCombinerMaker[protocols.T_Report]
    report_maker: protocols.ReportMaker[protocols.T_Report]
    report_scribe: protocols.VirtualDependencyScribe[
        protocols.T_VirtualDependency, protocols.T_Report
    ]

    def deploy_scribes(
        self, virtual_dependencies: protocols.VirtualDependencyMap[protocols.T_VirtualDependency]
    ) -> Iterator[protocols.WrittenVirtualDependency[protocols.T_Report]]:
        for virtual_dependency in virtual_dependencies.values():
            yield self.report_scribe(
                virtual_dependency=virtual_dependency,
                all_virtual_dependencies=virtual_dependencies,
            )

    def determine_version(
        self,
        *,
        destination: pathlib.Path,
        virtual_namespace: protocols.ImportPath,
        project_version: str,
        written_dependencies: Sequence[protocols.WrittenVirtualDependency[protocols.T_Report]],
    ) -> str:
        virtual_dep_hash = self.hasher(
            *(
                f"{written.virtual_import_path}:{written.summary_hash}".encode()
                for written in written_dependencies
            )
        )
        return f"{virtual_namespace}|{project_version}|written_deps:{virtual_dep_hash}"


def make_report_factory(
    *, hasher: protocols.Hasher
) -> protocols.ReportFactory[protocols.T_VirtualDependency, Report]:
    def report_scribe(
        *,
        virtual_dependency: protocols.T_VirtualDependency,
        all_virtual_dependencies: protocols.VirtualDependencyMap[protocols.T_VirtualDependency],
    ) -> protocols.WrittenVirtualDependency[Report]:
        return VirtualDependencyScribe(
            hasher=hasher,
            report_maker=Report,
            virtual_dependency=virtual_dependency,
            all_virtual_dependencies=all_virtual_dependencies,
        ).write()

    return ReportFactory(
        hasher=hasher,
        report_maker=Report,
        report_scribe=report_scribe,
        report_installer=ReportInstaller(
            _get_report_summary=VirtualDependencyScribe.get_report_summary
        ),
        report_combiner_maker=functools.partial(ReportCombiner, report_maker=Report),
    )


if TYPE_CHECKING:
    C_Report = Report
    C_CombinedReport = CombinedReport[Report]
    C_ReportFactory = ReportFactory[dependency.C_VirtualDependency, C_Report]
    C_ReportCombiner = ReportCombiner[C_Report]
    C_ReportInstaller = ReportInstaller
    C_WrittenVirtualDependency = WrittenVirtualDependency[C_Report]

    _R: protocols.P_Report = cast(Report, None)
    _RC: protocols.P_CombinedReport = cast(CombinedReport[protocols.P_Report], None)
    _RF: protocols.P_ReportFactory = cast(
        ReportFactory[protocols.P_VirtualDependency, protocols.P_Report], None
    )
    _WVD: protocols.P_WrittenVirtualDependency = cast(
        WrittenVirtualDependency[protocols.P_Report], None
    )
    _RI: protocols.P_ReportInstaller = cast(ReportInstaller, None)

    _CRC: protocols.ReportCombiner[C_Report] = cast(C_ReportCombiner, None)
    _CRCC: protocols.CombinedReport[C_Report] = cast(C_CombinedReport, None)
    _CRF: protocols.ReportFactory[dependency.C_VirtualDependency, C_Report] = cast(
        C_ReportFactory, None
    )
    _CRM: protocols.ReportMaker[C_Report] = C_Report
    _CWVD: protocols.WrittenVirtualDependency[C_Report] = cast(C_WrittenVirtualDependency, None)
