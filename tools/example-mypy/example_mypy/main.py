from extended_mypy_django_plugin.plugin import PluginProvider

from .plugin import ExampleMypyPlugin
from .virtual_dependencies import VirtualDependencyHandler

plugin = PluginProvider(ExampleMypyPlugin, VirtualDependencyHandler.create_report, locals())
