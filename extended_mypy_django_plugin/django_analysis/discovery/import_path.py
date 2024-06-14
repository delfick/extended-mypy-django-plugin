import types

from .. import protocols


class ImportPathHelper:
    def from_cls(self, cls: type) -> protocols.ImportPath:
        return self(f"{cls.__module__}.{cls.__qualname__}")

    def cls_module(self, cls: type) -> protocols.ImportPath:
        return self(cls.__module__)

    def from_module(self, module: types.ModuleType) -> protocols.ImportPath:
        return self(module.__name__)

    def __call__(self, path: str) -> protocols.ImportPath:
        if not all(part and part.isidentifier() for part in path.split(".")):
            raise RuntimeError(f"Provided path was not a valid python import path: '{path}'")
        return protocols.ImportPath(path)


ImportPath = ImportPathHelper()
