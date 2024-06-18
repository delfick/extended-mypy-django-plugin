from .entry import PluginProvider
from .plugin import DefaultVirtualDependencyHandler, ExtendedMypyStubs


class VirtualDependencyHandler(DefaultVirtualDependencyHandler):
    pass


plugin = PluginProvider(ExtendedMypyStubs, VirtualDependencyHandler.create, locals())
