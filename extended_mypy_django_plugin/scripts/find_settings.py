import pathlib
from collections.abc import Iterator
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.conf import LazySettings


def record_known_settings(output_location: pathlib.Path, settings: "LazySettings") -> None:
    found: set[str] = set()
    for line in find_known_settings(settings):
        found.add(line)

    output_location.write_text("\n".join(sorted(found)))


def find_known_settings(settings: "LazySettings") -> Iterator[str]:
    for name in dir(settings):
        if name.startswith("_"):
            continue

        yield f"{name} :: {type(getattr(settings, name))}"
