import os
import pathlib

from extended_mypy_django_plugin.django_analysis import hasher

tests_dir = pathlib.Path(__file__).parent.parent


class TestAdler32Hash:
    def test_it_creates_a_consistent_hash(self) -> None:
        found: dict[str, str] = {}
        contents: set[bytes] = set()
        for root, _, files in os.walk(tests_dir):
            for name in files:
                made: set[str] = set()
                content = (pathlib.Path(root) / name).read_bytes()
                if content in contents:
                    continue
                contents.add(content)

                for i in range(10):
                    made.add(hasher.adler32_hash(*content.splitlines()))

                # naive check to show the hash is consistent
                assert len(made) == 1
                hsh = next(iter(made))
                assert len(hsh) < 32
                found[name] = hsh

        # naive check to show the hash is different for different content
        assert len(set(found)) > 5
        assert len(set(found)) == len(set(found.values()))
