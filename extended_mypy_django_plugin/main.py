from .plugin import ExtendedMypyStubs, PluginProvider, VirtualDependencyHandler

plugin = PluginProvider(ExtendedMypyStubs, VirtualDependencyHandler.create_report, locals())
