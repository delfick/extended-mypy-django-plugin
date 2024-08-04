from ._plugin import hook, protocols
from ._plugin.config import ExtraOptions
from ._plugin.entry import PluginProvider
from ._plugin.plugin import ExtendedMypyStubs
from ._plugin.virtual_dependencies import VirtualDependencyHandler, VirtualDependencyHandlerBase

__all__ = [
    "hook",
    "protocols",
    "ExtraOptions",
    "PluginProvider",
    "ExtendedMypyStubs",
    "VirtualDependencyHandler",
    "VirtualDependencyHandlerBase",
]
