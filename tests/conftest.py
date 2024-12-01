import importlib

import pytest

pytest_plugins = ["pytest_typing_runner", "extended_mypy_django_plugin_test_driver.plugin"]


def pytest_report_header(config: pytest.Config) -> list[str] | None:
    return [f"Django: {importlib.metadata.version('django')}"]
