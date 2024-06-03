import importlib.metadata
import re
import textwrap
from collections.abc import Iterator

from pytest_mypy_plugins import OutputMatcher
from pytest_mypy_plugins.utils import (
    DaemonOutputMatcher,
    FileOutputMatcher,
    extract_output_matchers_from_out,
)
from typing_extensions import Self

regexes = {
    "reveal_tag": re.compile(
        r"^(?P<prefix_whitespace>\s*)#\s*\^\s*REVEAL\s+(?P<var_name>[^ ]+)\s*\^\s*(?P<rest>.*)"
    ),
}


class _Build:
    def __init__(self, for_daemon: bool) -> None:
        self.for_daemon = for_daemon
        self.result: list[OutputMatcher] = []
        self.daemon_should_restart: bool = False

    def add(
        self,
        path: str,
        lnum: int,
        col: int | None,
        severity: str,
        message: str,
        regex: bool = False,
    ) -> None:
        fname = path.removesuffix(".py")
        self.result.append(
            FileOutputMatcher(
                fname, lnum, severity, message, regex=regex, col=None if col is None else str(col)
            )
        )


class OutputBuilder:
    def __init__(
        self,
        build: _Build | None = None,
        target_file: str | None = None,
        for_daemon: bool | None = False,
    ) -> None:
        if build is None:
            assert for_daemon is not None
            build = _Build(for_daemon=for_daemon)
        self._build = build

        self.target_file = target_file

    def _normalise_message(self, message: str) -> str:
        if importlib.metadata.version("mypy") == "1.4.0":
            return message.replace("type[", "Type[").replace(
                "django.db.models.query.QuerySet", "django.db.models.query._QuerySet"
            )
        else:
            return message

    def clear(self) -> Self:
        self._build.result.clear()
        return self

    def daemon_should_restart(self) -> Self:
        self._build.daemon_should_restart = True
        return self

    def daemon_should_not_restart(self) -> Self:
        self._build.daemon_should_restart = False
        return self

    def on(self, path: str) -> Self:
        return self.__class__(build=self._build, target_file=path)

    def from_out(self, out: str, regex: bool = False) -> Self:
        if importlib.metadata.version("mypy") == "1.4.0":
            out = out.replace("type[", "Type[").replace(
                "django.db.models.query.QuerySet", "django.db.models.query._QuerySet"
            )

        self._build.result.extend(
            extract_output_matchers_from_out(
                out, {}, regex=regex, for_daemon=self._build.for_daemon
            )
        )
        return self

    def add_revealed_type(self, lnum: int, revealed_type: str) -> Self:
        revealed_type = self._normalise_message(revealed_type)

        assert self.target_file is not None
        self._build.add(
            self.target_file, lnum, None, "note", f'Revealed type is "{revealed_type}"'
        )
        return self

    def change_revealed_type(self, lnum: int, message: str) -> Self:
        message = self._normalise_message(message)

        assert self.target_file is not None

        found: list[FileOutputMatcher] = []
        for matcher in self._build.result:
            if (
                isinstance(matcher, FileOutputMatcher)
                and matcher.fname == self.target_file.removesuffix(".py")
                and matcher.lnum == lnum
                and matcher.severity == "note"
                and matcher.message.startswith("Revealed type is")
            ):
                found.append(matcher)

        assert len(found) == 1
        found[0].message = f'Revealed type is "{message}"'
        return self

    def remove_errors(self, lnum: int) -> Self:
        assert self.target_file is not None

        i: int = -1
        while i < len(self._build.result):
            if i >= len(self._build.result):
                break

            nxt = self._build.result[i]
            if (
                isinstance(nxt, FileOutputMatcher)
                and nxt.fname == self.target_file.removesuffix(".py")
                and nxt.lnum == lnum
                and nxt.severity == "error"
            ):
                self._build.result.pop(i)
            else:
                i += 1

        return self

    def add_error(self, lnum: int, error_type: str, message: str) -> Self:
        message = self._normalise_message(message)

        assert self.target_file is not None
        self._build.add(self.target_file, lnum, None, "error", f"{message}  [{error_type}]")
        return self

    def remove_from_revealed_type(self, lnum: int, remove: str) -> Self:
        remove = self._normalise_message(remove)

        assert self.target_file is not None

        found: list[FileOutputMatcher] = []
        for matcher in self._build.result:
            if (
                isinstance(matcher, FileOutputMatcher)
                and matcher.fname == self.target_file.removesuffix(".py")
                and matcher.lnum == lnum
                and matcher.severity == "note"
                and matcher.message.startswith("Revealed type is")
            ):
                found.append(matcher)

        assert len(found) == 1
        found[0].message = found[0].message.replace(remove, "")
        return self

    def parse_content(self, path: str, content: str | None) -> str | None:
        if content is None:
            return content

        content = textwrap.dedent(content).lstrip()
        result: list[str] = []
        expected = self.on(path)

        for i, line in enumerate(content.split("\n")):
            m = regexes["reveal_tag"].match(line)
            if m is None:
                if line.strip().startswith("#") and ("REVEAL" in line or "^" in line):
                    raise AssertionError(f"Found a potential reveal tag that was invalid:: {line}")
                result.append(line)
                continue

            gd = m.groupdict()
            result.append(f"{gd['prefix_whitespace']}reveal_type({gd['var_name']})")
            expected.add_revealed_type(i + 1, gd["rest"])

        return "\n".join(result)

    def __iter__(self) -> Iterator[OutputMatcher]:
        if self._build.daemon_should_restart and self._build.for_daemon:
            yield DaemonOutputMatcher(line="Restarting: plugins changed", regex=False)
            yield DaemonOutputMatcher(line="Daemon stopped", regex=False)
        yield from self._build.result
