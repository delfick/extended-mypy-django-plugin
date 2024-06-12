import pathlib

import pytest

from extended_mypy_django_plugin.django_analysis import Project, adler32_hash, analyzers, protocols

root_dir = pathlib.Path(__file__).parent.parent.parent


@pytest.fixture(scope="session")
def loaded_django_example() -> protocols.LoadedProject:
    project = Project(
        root_dir=root_dir / "example",
        hasher=adler32_hash,
        additional_sys_path=[str(root_dir)],
        analyzers=analyzers.Analyzers(
            analyze_known_models=analyzers.KnownModelsAnalyzer(),
            analyze_settings_types=analyzers.SettingsTypesAnalyzer(),
        ),
        env_vars={"DJANGO_SETTINGS_MODULE": "djangoexample.settings"},
    )
    return project.load_project()
