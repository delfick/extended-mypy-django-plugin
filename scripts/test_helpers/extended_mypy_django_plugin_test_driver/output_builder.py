import enum
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
from typing_extensions import Self, assert_never

regexes = {
    "potential_instruction": re.compile(r"^\s*#\s*\^"),
    "instruction": re.compile(
        r"^(?P<prefix_whitespace>\s*)#\s*\^\s*(?P<instruction>REVEAL|ERROR|NOTE)(?P<options>\([^\)]*)?(?P<tag>\[[^\]]*\])?\s*\^\s*(?P<rest>.*)"
    ),
    "assignment": re.compile(r"^(?P<var_name>[a-zA-Z0-9_]+)\s*(:[^=]+)?(=|$)"),
}


class _Instruction(enum.Enum):
    REVEAL = "REVEAL"
    ERROR = "ERROR"
    NOTE = "NOTE"


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

        lines = content.split("\n")
        for i, line in enumerate(lines):
            m = regexes["instruction"].match(line)
            if m is None:
                if regexes["potential_instruction"].match(line):
                    raise AssertionError(
                        f"Looks like line is trying to be an expectation but it didn't pass the regex for one: {line}"
                    )
                result.append(line)
                continue

            gd = m.groupdict()
            result.append("")
            expected._parse_instruction(
                i,
                result,
                line,
                prefix_whitespace=gd["prefix_whitespace"],
                instruction=_Instruction(gd["instruction"]),
                options=gd.get("options", ""),
                tag=gd.get("tag", ""),
                rest=gd["rest"],
            )

        return "\n".join(result)

    def _parse_instruction(
        self,
        i: int,
        result: list[str],
        line: str,
        *,
        prefix_whitespace: str,
        instruction: _Instruction,
        options: str,
        tag: str,
        rest: str,
    ) -> None:
        if instruction is _Instruction.REVEAL:
            previous_line = result[i - 1]
            m = regexes["assignment"].match(previous_line.strip())
            if m:
                result[i] = f"{prefix_whitespace}reveal_type({m.groupdict()['var_name']})"
                i += 1
            else:
                result[i - 1] = f"{prefix_whitespace}reveal_type({previous_line.strip()})"

            self.add_revealed_type(i, rest)
        elif instruction is _Instruction.ERROR:
            raise NotImplementedError()
        elif instruction is _Instruction.NOTE:
            raise NotImplementedError()
        else:
            assert_never(instruction)

    def __iter__(self) -> Iterator[OutputMatcher]:
        if self._build.daemon_should_restart and self._build.for_daemon:
            yield DaemonOutputMatcher(line="Restarting: plugins changed", regex=False)
            yield DaemonOutputMatcher(line="Daemon stopped", regex=False)
        yield from self._build.result
