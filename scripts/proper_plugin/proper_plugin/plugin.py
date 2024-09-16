try:
    from mypy.plugins.proper_plugin import plugin
except ImportError:
    from mypy.plugin import Plugin

    def plugin(version: str) -> type[Plugin]:
        return Plugin
