import dataclasses
from typing import TYPE_CHECKING, cast

from .. import protocols
from ..discovery.import_path import ImportPath


@dataclasses.dataclass
class VirtualDependencyNamer:
    namespace: protocols.ImportPath
    hasher: protocols.Hasher

    def __call__(self, module: protocols.ImportPath, /) -> protocols.ImportPath:
        return ImportPath(f"{self.namespace}.mod_{self.hasher(module.encode())}")


if TYPE_CHECKING:
    _VDN: protocols.VirtualDependencyNamer = cast(VirtualDependencyNamer, None)
