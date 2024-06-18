import pathlib

import pytest

from extended_mypy_django_plugin.django_analysis import Project, discovery, protocols

root_dir = pathlib.Path(__file__).parent.parent.parent


@pytest.fixture(scope="session")
def loaded_django_example() -> protocols.Loaded[Project]:
    return Project(
        root_dir=root_dir / "example",
        additional_sys_path=[str(root_dir)],
        discovery=discovery.Discovery(),
        env_vars={"DJANGO_SETTINGS_MODULE": "djangoexample.settings"},
    ).load_project()


@pytest.fixture(scope="session")
def discovered_django_example(
    loaded_django_example: protocols.Loaded[Project],
) -> protocols.Discovered[Project]:
    return loaded_django_example.perform_discovery()
