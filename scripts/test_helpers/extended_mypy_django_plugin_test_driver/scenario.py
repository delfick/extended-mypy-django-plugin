import ast
import dataclasses
import inspect
import pathlib
import subprocess
import sys
import tempfile
import textwrap
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, TypeVar, cast

from pytest_typing_runner import builders, file_changers, protocols, scenarios
from typing_extensions import Self

scripts_dir = pathlib.Path(__file__).parent.parent.parent

T_Scenario = TypeVar("T_Scenario", bound="Scenario")


@dataclasses.dataclass(kw_only=True)
class ScenarioInfo:
    django_settings_module: str = "mysettings"
    mypy_configuration_filename: str = "mypy.ini"
    mypy_configuration_content: str = """
        [mypy]
        mypy_path = $MYPY_CONFIG_FILE_DIR/.mypy_django_scratch/test

        plugins =
            extended_mypy_django_plugin.main

        [mypy.plugins.django-stubs]
        scratch_path = $MYPY_CONFIG_FILE_DIR/.mypy_django_scratch/test
        django_settings_module = {django_settings_module}
        """
    additional_mypy_configuration_content: str = ""
    copied_apps: list[str] = dataclasses.field(default_factory=list)
    installed_apps: list[str] = dataclasses.field(default_factory=list)
    monkeypatch: bool = False
    debug: bool = False
    change_settings: Callable[[str], str] | None = None


@dataclasses.dataclass(frozen=True, kw_only=True)
class Scenario(scenarios.Scenario):
    info: ScenarioInfo = dataclasses.field(default_factory=ScenarioInfo)

    def copy_django_app(
        self,
        app: str,
        file_modification: protocols.FileModifier,
        skip_if_destination_exists: bool = True,
    ) -> None:
        location = scripts_dir / app
        if location.exists() and location.is_dir() and location.is_relative_to(scripts_dir):
            file_changers.CopyDirectory(root_dir=self.root_dir, src=scripts_dir, path=app).do_copy(
                modify_file=file_modification,
                exclude=lambda p: p.suffix == ".pyc",
                skip_if_destination_exists=skip_if_destination_exists,
            )

    def determine_django_settings_content(
        self, settings_path: str, options: protocols.RunOptions[Self]
    ) -> str:
        found = {}

        def register_value(*, variable_name: str, value: object) -> None:
            found[variable_name] = value

        def change_installed_apps(
            *, variable_name: str, values: Sequence[object]
        ) -> Sequence[ast.expr]:
            value = self.info.installed_apps

            if "django.contrib.contenttypes" not in value:
                value = list(value)
                value.insert(0, "django.contrib.contenttypes")

            return [ast.Constant(value=app) for app in value if isinstance(app, str)]

        new_settings = file_changers.BasicPythonAssignmentChanger(
            cwd=options.cwd,
            root_dir=self.root_dir,
            path=settings_path,
            variable_changers={
                "SECRET_KEY": file_changers.VariableFinder(notify=register_value),
                "INSTALLED_APPS": file_changers.ListVariableChanger(change=change_installed_apps),
            },
        ).after_change(default_content="INSTALLED_APPS=[]")

        if "SECRET_KEY" not in found:
            new_settings = f"{new_settings}\nSECRET_KEY = '1'"

        monkeypatch_str = "import django_stubs_ext\ndjango_stubs_ext.monkeypatch()\n"
        new_settings = new_settings.replace(monkeypatch_str, "")
        if self.info.monkeypatch:
            new_settings = monkeypatch_str + new_settings

        if self.info.change_settings:
            new_settings = self.info.change_settings(new_settings)

        return new_settings

    def create_django_settings(
        self, *, options: protocols.RunOptions[Self], file_modification: protocols.FileModifier
    ) -> None:
        file_modification(
            path=self.info.mypy_configuration_filename,
            content=(
                self.info.mypy_configuration_content.format(
                    django_settings_module=self.info.django_settings_module
                )
                + "\n"
                + self.info.additional_mypy_configuration_content
            ),
        )

        settings_path = f"{self.info.django_settings_module}.py"
        settings_content = self.determine_django_settings_content(
            options=options, settings_path=settings_path
        )
        file_modification(
            path=settings_path,
            content=settings_content,
        )


@dataclasses.dataclass(frozen=True, kw_only=True)
class ScenarioRunner(scenarios.ScenarioRunner[Scenario]):
    def execute_static_checking(
        self, options: protocols.RunOptions[Scenario]
    ) -> protocols.NoticeChecker[Scenario]:
        if self.scenario.info.debug:
            pathlib.Path("/tmp/debug").write_text("")
        else:
            pathlib.Path("/tmp/debug").unlink(missing_ok=True)

        self.scenario.create_django_settings(
            options=options, file_modification=self.file_modification
        )
        return super().execute_static_checking(options=options)


@dataclasses.dataclass(frozen=True, kw_only=True)
class ScenarioFile(builders.ScenarioFile):
    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class ScenarioBuilder(builders.ScenarioBuilder[Scenario, ScenarioFile]):
    def copy_django_apps(self, *apps: str) -> Self:
        def file_modification(path: str, content: str | None) -> None:
            self.on(path).set(content)

        for app in apps:
            self.scenario_runner.scenario.copy_django_app(app, file_modification)

        return self

    def set_installed_apps(self, *apps: str) -> Self:
        self.scenario_runner.scenario.info.installed_apps = list(apps)
        return self

    def set_and_copy_installed_apps(self, *apps: str) -> Self:
        self.set_installed_apps(*apps)
        self.copy_django_apps(*apps)
        return self

    def populate_virtual_deps(self, *, deps_dest: pathlib.Path) -> None:
        options = self.determine_options()
        self.scenario_runner.scenario.create_django_settings(
            options=options, file_modification=self.scenario_runner.file_modification
        )

        def populate(
            cwd: pathlib.Path, django_settings_module: str, deps_dest: pathlib.Path
        ) -> None:
            from extended_mypy_django_plugin.plugin import VirtualDependencyHandler

            class DependencyHandler(VirtualDependencyHandler):
                def interface_differentiator(self) -> str:
                    return "timestamp"

            DependencyHandler.create_report(
                project_root=cwd,
                django_settings_module=django_settings_module,
                virtual_deps_destination=deps_dest,
            )

        mainline = """
        if __name__ == "__main__":
            populate(pathlib.Path(sys.argv[1]), sys.argv[2], pathlib.Path(sys.argv[3]))
        """

        content = [
            "import pathlib",
            "import sys",
            textwrap.dedent(inspect.getsource(populate)),
            textwrap.dedent(mainline),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            script = pathlib.Path(tmpdir, "script.py")
            script.write_text("\n".join(content))
            subprocess.check_call(
                [
                    sys.executable,
                    str(script),
                    str(options.cwd),
                    self.scenario_runner.scenario.info.django_settings_module,
                    str(deps_dest),
                ]
            )


if TYPE_CHECKING:
    _S: protocols.Scenario = cast(Scenario, None)
    _SF: protocols.P_ScenarioFile = cast(ScenarioFile, None)
    _SR: protocols.ScenarioRunner[Scenario] = cast(ScenarioRunner, None)
