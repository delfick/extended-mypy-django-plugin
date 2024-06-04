import dataclasses
import importlib.resources
import importlib.util
import io
import itertools
import pathlib
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import textwrap
import time
import zlib
from collections import defaultdict
from collections.abc import Iterator, Mapping, MutableMapping
from typing import Any, ClassVar, Protocol, Union

from django.db import models
from django.db.models.fields.related import ForeignObjectRel, RelatedField

ModelModules = Mapping[str, Mapping[str, type[models.Model]]]


regexes = {
    "mod_decl": re.compile(r'^mod = "(?P<mod>[^"]+)"$'),
    "summary_decl": re.compile(r'^summary = "(?P<summary>[^"]+)"$'),
}


class ModelRelatedFieldsGetter(Protocol):
    def __call__(self, model_cls: type[models.Model]) -> Iterator["RelatedField[Any, Any]"]: ...


class FieldRelatedModelClsGetter(Protocol):
    def __call__(
        self, field: Union["RelatedField[Any, Any]", ForeignObjectRel]
    ) -> type[models.Model]: ...


class ReportNamesGetter(Protocol):
    def __call__(self, fullname: str, deps: set[str], /) -> Iterator[str]: ...


@dataclasses.dataclass
class _Store:
    prefix: str
    reports_dir: pathlib.Path

    modules: Mapping[str, str] = dataclasses.field(default_factory=dict)
    modules_to_report_name: MutableMapping[str, str] = dataclasses.field(default_factory=dict)

    version: ClassVar[str] = "json.1"

    @classmethod
    def read(cls, prefix: str, reports_dir: pathlib.Path) -> "_Store":
        modules: dict[str, str] = {}
        if not reports_dir.exists():
            reports_dir.mkdir(parents=True, exist_ok=True)

        for path in reports_dir.iterdir():
            mod: str | None = None
            summary: str | None = None

            if path.is_dir():
                shutil.rmtree(path)
                continue

            if path.suffix == ".py":
                for line in path.read_text().splitlines():
                    m = regexes["mod_decl"].match(line)
                    if m:
                        mod = m.groupdict()["mod"]

                    m = regexes["summary_decl"].match(line)
                    if m:
                        summary = m.groupdict()["summary"]

            if mod is None or summary is None:
                path.unlink()
            else:
                try:
                    spec = importlib.util.find_spec(mod)
                except ModuleNotFoundError:
                    spec = None

                if spec:
                    modules[mod] = summary
                else:
                    path.unlink()

        return cls(prefix=prefix, modules=modules, reports_dir=reports_dir).write(modules)

    def _write_mod(
        self, directory: pathlib.Path, mod: str, summary: str, empty: bool = False
    ) -> str:
        name = f"mod_{zlib.adler32(mod.encode())}"
        self.modules_to_report_name[mod] = f"{self.prefix}.{name}"

        # For mypy to trigger this dependency as stale it's interface must change
        # So we produce a different function each time using the current time
        content = textwrap.dedent(f"""
        def value_{'not_installed' if empty else str(time.time()).replace('.', '__')}() -> str:
            return ""

        mod = "{mod}"
        summary = "{summary}"
        """)

        destination = self.reports_dir / f"{name}.py"
        previous_summary: str | None = None
        if destination.exists():
            for line in destination.read_text().splitlines():
                m = regexes["summary_decl"].match(line)
                if m:
                    previous_summary = m.groupdict()["summary"]
                    break

        if summary != previous_summary:
            (directory / f"{name}.py").write_text(content)
        return name

    def add_mod(self, mod: str) -> str:
        with tempfile.TemporaryDirectory(dir=self.reports_dir, prefix=".tmp") as tmp:
            temp_dir = pathlib.Path(tmp)
            summary = f"{mod} ||>"
            name = self._write_mod(temp_dir, mod, summary, empty=True)
            made = temp_dir / f"{name}.py"
            if made.exists():
                made.rename(self.reports_dir / f"{name}.py")
            return f"{self.prefix}.{name}"

    def write(self, modules: Mapping[str, str]) -> "_Store":
        instance = self.__class__(
            prefix=self.prefix,
            modules=modules,
            reports_dir=self.reports_dir,
            modules_to_report_name=self.modules_to_report_name,
        )

        # Prevent partial writes by dumping to a temp directory and moving changed files
        # We also don't simply rename the entire directory so unchanged files remain unchanged
        with tempfile.TemporaryDirectory(dir=self.reports_dir, prefix=".tmp") as tmp:
            temp_dir = pathlib.Path(tmp)
            for mod, summary in instance.modules.items():
                instance._write_mod(temp_dir, mod, summary)

            for path in temp_dir.iterdir():
                destination = instance.reports_dir / path.name
                if not destination.exists():
                    path.rename(destination)
                elif path.read_bytes() != destination.read_bytes():
                    path.rename(destination)

        return instance


class _DepFinder:
    @classmethod
    def find_from(
        cls,
        model_modules: ModelModules,
        django_settings_module: str,
        get_model_related_fields: ModelRelatedFieldsGetter,
        get_field_related_model_cls: FieldRelatedModelClsGetter,
    ) -> tuple[Mapping[str, set[str]], Mapping[str, set[str]]]:
        instance = cls(model_modules=model_modules, django_settings_module=django_settings_module)
        found: set[str] = {django_settings_module}

        for mod, known in model_modules.items():
            found.add(mod)
            for name, model_cls in known.items():
                instance._find_models_in_mro(mod, model_cls)
                instance._find_related_models(
                    mod,
                    model_cls,
                    get_model_related_fields,
                    get_field_related_model_cls=get_field_related_model_cls,
                )

        result: dict[str, set[str]] = {}
        for mod in found:
            result[mod] = (
                set()
                .union(instance.known_models.get(mod) or set())
                .union(instance.related_models.get(mod) or set())
            )
        return result, instance.model_children

    def __init__(self, *, model_modules: ModelModules, django_settings_module: str) -> None:
        self.model_modules = model_modules
        self.django_settings_modules = django_settings_module

        self.related_models: dict[str, set[str]] = defaultdict(set)
        self.known_models: dict[str, set[str]] = defaultdict(set)
        self.model_children: dict[str, set[str]] = defaultdict(set)

    def _find_models_in_mro(self, mod: str, cls: type[models.Model]) -> None:
        cls_fullname = f"{cls.__module__}.{cls.__qualname__}"
        self.known_models[mod].add(cls_fullname)
        self.model_children[cls_fullname].add(cls_fullname)

        for mro in cls.mro():
            if mro is cls:
                continue
            if mro is models.Model:
                break

            mro_fullname = f"{mro.__module__}.{mro.__qualname__}"

            if mro.__module__ != mod:
                self.known_models[mod].add(mro_fullname)

            if not mro.__module__.startswith("django."):
                self.known_models[mro.__module__].add(cls_fullname)
                self.model_children[mro_fullname].add(cls_fullname)

    def _find_related_models(
        self,
        mod: str,
        cls: type[models.Model],
        get_model_related_fields: ModelRelatedFieldsGetter,
        get_field_related_model_cls: FieldRelatedModelClsGetter,
    ) -> None:
        cls_fullname = "{cls.__module__}.{cls.__qualname__}"

        for field in itertools.chain(
            # forward relations
            get_model_related_fields(cls),
            # reverse relations - `related_objects` is private API (according to docstring)
            cls._meta.related_objects,  # type: ignore[attr-defined]
        ):
            try:
                related_model_cls = get_field_related_model_cls(field)
            except Exception:
                continue

            else:
                if related_model_cls is None:
                    continue
            related_model_module = related_model_cls.__module__
            related_model_fullname = (
                f"{related_model_cls.__module__}.{related_model_cls.__qualname__}"
            )
            if related_model_module != mod:
                self.related_models[mod].add(related_model_fullname)
                if not related_model_module.startswith("django."):
                    self.related_models[related_model_module].add(cls_fullname)


class Reports:
    """
    This class is responsible for generating the files that represent our virtual
    dependencies.

    Further documentation has yet to be added.
    """

    @classmethod
    def create(
        cls,
        *,
        determine_django_state_script: pathlib.Path | None,
        django_settings_module: str,
        scratch_path: pathlib.Path,
        reports_dir_prefix: str = "__virtual_extended_mypy_django_plugin_report__",
    ) -> "Reports":
        if determine_django_state_script is not None:
            if not determine_django_state_script.exists():
                raise ValueError("The provided script for finding installed apps does not exist")

            if not determine_django_state_script.stat().st_mode & stat.S_IXUSR:
                raise ValueError(
                    "The provided script for finding installed apps is not executable!"
                )

        if determine_django_state_script is None:
            determine_django_state_script = pathlib.Path(
                str(
                    importlib.resources.files("extended_mypy_django_plugin")
                    / "scripts"
                    / "determine_django_state.py"
                )
            )

        reports_dir = scratch_path / reports_dir_prefix
        if reports_dir.exists() and not reports_dir.is_dir():
            reports_dir.unlink()
        reports_dir.mkdir(parents=True, exist_ok=True)

        return cls(
            store=_Store.read(prefix=reports_dir_prefix, reports_dir=reports_dir),
            determine_django_state_script=determine_django_state_script,
            django_settings_module=django_settings_module,
        )

    def __init__(
        self,
        *,
        store: _Store,
        determine_django_state_script: pathlib.Path,
        django_settings_module: str,
    ) -> None:
        self._store = store
        self._determine_django_state_script = determine_django_state_script
        self._django_settings_module = django_settings_module
        self._known_concrete_models: MutableMapping[str, set[str]] = defaultdict(set)

    def known_concrete_models(self, fullname: str) -> set[str]:
        return self._known_concrete_models[fullname]

    def lines_hash(self) -> str:
        buffer = io.BytesIO()
        for path in self._store.reports_dir.iterdir():
            valid_dependency = (
                path.is_file() and path.suffix == ".py" and not path.name.startswith(".")
            )
            if not valid_dependency:
                continue

            content = path.read_bytes()
            if b"def value_not_installed" not in content:
                buffer.write(b"\n")
                buffer.write(path.name.encode())
                buffer.write(b"\n")
                buffer.write(path.read_bytes())

        return str(zlib.adler32(buffer.getbuffer()))

    def determine_version_hash(
        self, scratch_path: pathlib.Path, previous_version: int | None
    ) -> int:
        result_file_cm = tempfile.NamedTemporaryFile()
        known_models_file_cm = tempfile.NamedTemporaryFile()
        with result_file_cm as result_file, known_models_file_cm as known_models_file:
            if self._determine_django_state_script is not None:
                script = self._determine_django_state_script
            else:
                script = pathlib.Path(
                    str(
                        importlib.resources.files("extended_mypy_django_plugin")
                        / "scripts"
                        / "determine_django_state.py"
                    )
                )

            cmd: list[str] = []

            if script.suffix == ".py":
                cmd.append(sys.executable)
            else:
                with open(script) as fle:
                    line = fle.readline()
                    if line.startswith("#!"):
                        cmd.extend(shlex.split(line[2:]))

            cmd.extend(
                [
                    str(script),
                    "--django-settings-module",
                    self._django_settings_module,
                    "--apps-file",
                    result_file.name,
                    "--known-models-file",
                    known_models_file.name,
                    "--scratch-path",
                    str(scratch_path),
                ]
            )

            try:
                subprocess.run(cmd, capture_output=True, check=True)
            except subprocess.CalledProcessError as err:
                if err.returncode == 2:
                    return 1 if previous_version is None else previous_version
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
                        raise RuntimeError("\n".join(message)) from None

            installed_apps_hash = str(zlib.adler32(pathlib.Path(result_file.name).read_bytes()))
            known_models_hash = str(
                zlib.adler32(pathlib.Path(known_models_file.name).read_bytes())
            )
            return zlib.adler32(
                f"{installed_apps_hash}.{known_models_hash}.{self.lines_hash()}".encode()
            )

    def report_names_getter(
        self,
        installed_apps: list[str],
        model_modules: ModelModules,
        get_model_related_fields: ModelRelatedFieldsGetter,
        get_field_related_model_cls: FieldRelatedModelClsGetter,
    ) -> ReportNamesGetter:
        summaries: dict[str, str] = {}
        installed_apps_hash = f"installed_apps:{zlib.adler32('||'.join(installed_apps).encode())}"
        results, model_children = _DepFinder.find_from(
            model_modules,
            django_settings_module=self._django_settings_module,
            get_model_related_fields=get_model_related_fields,
            get_field_related_model_cls=get_field_related_model_cls,
        )
        for mod, deps in results.items():
            deps_hash = f"deps:{zlib.adler32('||'.join(sorted(deps)).encode())}"
            summaries[mod] = f"{mod} |>> {self._store.prefix}.{installed_apps_hash}.{deps_hash}"

        self._store = self._store.write(summaries)
        self._known_concrete_models.update(model_children)
        return self._get_report_names

    def _get_report_names(self, fullname: str, deps: set[str], /) -> Iterator[str]:
        report = self._store.modules_to_report_name.get(fullname)
        if report is None:
            if fullname.startswith("django.db."):
                return

            if ".models." in fullname or fullname.endswith(".models"):
                report = self._store.add_mod(fullname)

        if report is not None:
            yield report

        if fullname == self._django_settings_module:
            return

        if report or fullname.startswith(f"{self._store.prefix}."):
            yield self._store.modules_to_report_name[self._django_settings_module]
            yield self._django_settings_module

        for dep in deps:
            report = self._store.modules_to_report_name.get(dep)
            if report and report not in deps:
                yield report
