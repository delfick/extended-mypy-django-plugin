import functools

import pytest
from pytest_typing_runner import parse, protocols

from .scenario import Scenario, ScenarioBuilder, ScenarioFile, ScenarioRunner


@pytest.fixture
def typing_scenario_maker() -> protocols.ScenarioMaker[Scenario]:
    return Scenario.create


@pytest.fixture
def typing_scenario_runner_maker() -> protocols.ScenarioRunnerMaker[Scenario]:
    return ScenarioRunner.create


@pytest.fixture
def builder(typing_scenario_runner: ScenarioRunner) -> ScenarioBuilder:
    return ScenarioBuilder(
        scenario_runner=typing_scenario_runner,
        scenario_file_maker=functools.partial(
            ScenarioFile,
            file_parser=parse.FileContent().parse,
            file_modification=typing_scenario_runner.file_modification,
        ),
    )


@pytest.fixture
def scenario(typing_scenario_runner: ScenarioRunner) -> Scenario:
    return typing_scenario_runner.scenario


@pytest.fixture
def scenario_runner(typing_scenario_runner: ScenarioRunner) -> ScenarioRunner:
    return typing_scenario_runner
