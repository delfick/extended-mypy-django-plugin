import zlib
from typing import TYPE_CHECKING

from . import protocols


def adler32_hash(*parts: bytes) -> str:
    return str(zlib.adler32(b"\n".join(parts)))


if TYPE_CHECKING:
    _a32h: protocols.Hasher = adler32_hash
