from ._plugin import protocols
from ._plugin.config import ExtraOptions
from ._plugin.entry import PluginProvider
from ._plugin.hook import Hook, hook
from ._plugin.plugin import ExtendedMypyStubs
from ._plugin.virtual_dependencies import VirtualDependencyHandler, VirtualDependencyHandlerBase

__all__ = [
    "hook",
    "Hook",
    "protocols",
    "ExtraOptions",
    "PluginProvider",
    "ExtendedMypyStubs",
    "VirtualDependencyHandler",
    "VirtualDependencyHandlerBase",
]
