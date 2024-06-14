import functools
import pathlib

import pytest

from extended_mypy_django_plugin.django_analysis import (
    Field,
    Model,
    Module,
    Project,
    discovery,
    protocols,
)

root_dir = pathlib.Path(__file__).parent.parent.parent


@pytest.fixture(scope="session")
def loaded_django_example() -> protocols.Loaded[Project]:
    field_creator = Field.create
    model_creator = functools.partial(Model.create, field_creator=field_creator)
    module_creator = functools.partial(Module.create, model_creator=model_creator)

    project = Project(
        root_dir=root_dir / "example",
        additional_sys_path=[str(root_dir)],
        discovery=discovery.Discovery(
            discover_installed_models=discovery.DefaultInstalledModulesDiscovery(
                module_creator=module_creator
            ),
            discover_settings_types=discovery.NaiveSettingsTypesDiscovery(),
            discover_concrete_models=discovery.ConcreteModelsDiscovery(),
        ),
        env_vars={"DJANGO_SETTINGS_MODULE": "djangoexample.settings"},
    )
    return project.load_project()


@pytest.fixture(scope="session")
def discovered_django_example(
    loaded_django_example: protocols.Loaded[Project],
) -> protocols.Discovered[Project]:
    return loaded_django_example.perform_discovery()
