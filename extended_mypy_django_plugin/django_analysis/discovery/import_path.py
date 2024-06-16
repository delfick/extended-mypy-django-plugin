import types

from .. import protocols


class InvalidImportPath(ValueError):
    pass


class ImportPathHelper:
    """
    Helper for creating strings that are valid protocols.ImportPath objects
    """

    def from_cls(self, cls: type) -> protocols.ImportPath:
        """
        Given some class return an import path to it
        """
        return self(f"{cls.__module__}.{cls.__qualname__}")

    def cls_module(self, cls: type) -> protocols.ImportPath:
        """
        Given some cls return an import path to the module that defined it
        """
        return self(cls.__module__)

    def from_module(self, module: types.ModuleType) -> protocols.ImportPath:
        """
        Given some module return an import path to it
        """
        return self(module.__name__)

    def split(
        self, path: protocols.ImportPath
    ) -> tuple[protocols.ImportPath, protocols.ImportPath]:
        """
        Split a path into it's namespace and name.

        So `my.code.Thing` splits into (`my.code`, `Thing`)

        If the path is not namespaced then a InvalidImportPath will be raised
        """
        if "." not in path:
            raise InvalidImportPath(f"Provided path was not namespaced: '{path}'")
        namespace, name = path.rsplit(".", 1)
        return protocols.ImportPath(namespace), protocols.ImportPath(name)

    def __call__(self, path: str) -> protocols.ImportPath:
        """
        Return a string as a protocols.ImportPath type.

        If the string is not a valid import then a InvalidImportPath will be raised
        """
        if not all(part and part.isidentifier() for part in path.split(".")):
            raise InvalidImportPath(f"Provided path was not a valid python import path: '{path}'")
        return protocols.ImportPath(path)


ImportPath = ImportPathHelper()
