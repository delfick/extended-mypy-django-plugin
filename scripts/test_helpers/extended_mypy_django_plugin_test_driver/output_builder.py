import collections
import dataclasses
import enum
import importlib.metadata
import re
import textwrap
from collections.abc import Iterator, Sequence
from itertools import chain

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
        r"^(?P<prefix_whitespace>\s*)#\s*\^\s*(?P<instruction>TAG|REVEAL|ERROR|NOTE)(\((?P<options>[^\)]*)\))?(\[(?P<tag>[^\]]*)\])?\s*\^\s*(?P<rest>.*)"
    ),
    "assignment": re.compile(r"^(?P<var_name>[a-zA-Z0-9_]+)\s*(:[^=]+)?(=|$)"),
}


class _Instruction(enum.Enum):
    TAG = "TAG"
    REVEAL = "REVEAL"
    ERROR = "ERROR"
    NOTE = "NOTE"


class _Build:
    @dataclasses.dataclass
    class _File:
        tags: dict[str, FileOutputMatcher] = dataclasses.field(default_factory=dict)
        matchers: list[FileOutputMatcher] = dataclasses.field(default_factory=list)

        def clear(self) -> None:
            self.tags.clear()
            self.matchers.clear()

    def __init__(self, for_daemon: bool) -> None:
        self.for_daemon = for_daemon
        self._by_file: dict[str, _Build._File] = collections.defaultdict(lambda: _Build._File())
        self.daemon_should_restart: bool = False

    @property
    def result(self) -> Sequence[OutputMatcher]:
        return list(chain.from_iterable([f.matchers for f in self._by_file.values()]))

    def matcher_for_tag(self, path: str, tag: str) -> FileOutputMatcher:
        if path not in self._by_file or tag not in self._by_file[path].tags:
            raise AssertionError(f"No previously made matcher for {path} with tag {tag}")

        return self._by_file[path].tags[tag]

    def remove_tagged(self, path: str, tag: str, leave_tag: bool = False) -> None:
        lnum = self.matcher_for_tag(path, tag).lnum
        self._by_file[path].matchers = [
            matcher for matcher in self._by_file[path].matchers if matcher.lnum != lnum
        ]
        if not leave_tag:
            del self._by_file[path].tags[tag]

    def add(
        self,
        path: str,
        lnum: int,
        col: int | None,
        severity: str,
        message: str,
        regex: bool = False,
        tag: str = "",
        tag_only: bool = False,
        override_tag: bool = False,
    ) -> None:
        fname = path.removesuffix(".py")
        matcher = FileOutputMatcher(
            fname, lnum, severity, message, regex=regex, col=None if col is None else str(col)
        )

        for_file = self._by_file[path]

        existing_matcher: FileOutputMatcher | None = None
        if tag and override_tag and tag in for_file.tags:
            existing_matcher = for_file.tags[tag]

        if not tag_only:
            if tag and override_tag and tag in for_file.tags:
                for_file.matchers = [
                    matcher for matcher in for_file.matchers if matcher is not existing_matcher
                ]

            for_file.matchers.append(matcher)

        if tag:
            if not override_tag:
                assert (
                    tag not in for_file.tags
                ), f"Already have a matched tagged as {tag} for {path}"
            for_file.tags[tag] = matcher

    def clear_path(self, path: str) -> None:
        self._by_file[path].clear()

    def clear(self) -> None:
        self._by_file.clear()


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
            return (
                message.replace("type[", "Type[")
                .replace("django.db.models.query.QuerySet", "django.db.models.query._QuerySet")
                .replace("Type[Concrete?", "type[Concrete?")
            )
        else:
            return message

    def _split_lnum_or_tag(self, lnum_or_tag: int | str) -> tuple[int, str]:
        if isinstance(lnum_or_tag, int):
            return lnum_or_tag, ""
        else:
            return -1, lnum_or_tag

    def clear(self) -> Self:
        if self.target_file:
            self._build.clear_path(self.target_file)
        else:
            self._build.clear()
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

        for matcher in extract_output_matchers_from_out(
            out, {}, regex=regex, for_daemon=self._build.for_daemon
        ):
            assert isinstance(matcher, FileOutputMatcher)
            self._build._by_file[f"{matcher.fname}.py"].matchers.append(matcher)
        return self

    def add_revealed_type(self, lnum_or_tag: int | str, revealed_type: str, tag: str = "") -> Self:
        assert self.target_file is not None

        revealed_type = self._normalise_message(revealed_type)

        lnum, itag = self._split_lnum_or_tag(lnum_or_tag)

        if itag:
            if not tag:
                tag = itag
            lnum = self._build.matcher_for_tag(self.target_file, tag).lnum

        self._build.add(
            self.target_file,
            lnum,
            None,
            "note",
            f'Revealed type is "{revealed_type}"',
            tag=tag,
            override_tag=True,
        )
        return self

    def remove_errors(self, lnum_or_tag: int | str, leave_tag: bool = False) -> Self:
        assert self.target_file is not None

        lnum, tag = self._split_lnum_or_tag(lnum_or_tag)

        if tag:
            self._build.remove_tagged(self.target_file, tag, leave_tag=leave_tag)
            return self

        self._build._by_file[self.target_file].matchers = [
            matcher
            for matcher in self._build._by_file[self.target_file].matchers
            if matcher.lnum != lnum and matcher.severity != "error"
        ]

        return self

    def add_error(
        self, lnum_or_tag: int | str, error_type: str, message: str, tag: str = ""
    ) -> Self:
        assert self.target_file is not None

        message = self._normalise_message(message)

        lnum, itag = self._split_lnum_or_tag(lnum_or_tag)

        if itag:
            if not tag:
                tag = itag
            lnum = self._build.matcher_for_tag(self.target_file, tag).lnum

        self._build.add(
            self.target_file,
            lnum,
            None,
            "error",
            f"{message}  [{error_type}]",
            tag=tag,
            override_tag=True,
        )
        return self

    def replace_errors(self, tag: str, *errors: tuple[str, str]) -> Self:
        assert self.target_file is not None

        lnum = self._build.matcher_for_tag(self.target_file, tag).lnum
        self.remove_errors(tag, leave_tag=True)

        for error_type, message in errors:
            self.add_error(lnum, error_type, message)

        return self

    def add_note(self, lnum_or_tag: int | str, message: str, tag: str = "") -> Self:
        assert self.target_file is not None

        message = self._normalise_message(message)

        lnum, itag = self._split_lnum_or_tag(lnum_or_tag)

        if itag:
            if not tag:
                tag = itag
            lnum = self._build.matcher_for_tag(self.target_file, tag).lnum

        self._build.add(self.target_file, lnum, None, "note", message, tag=tag, override_tag=True)
        return self

    def remove_from_revealed_type(self, lnum_or_tag: int | str, remove: str) -> Self:
        assert self.target_file is not None

        remove = self._normalise_message(remove)

        lnum, tag = self._split_lnum_or_tag(lnum_or_tag)

        if tag:
            lnum = self._build.matcher_for_tag(self.target_file, tag).lnum

        found: list[FileOutputMatcher] = []
        for matcher in self._build._by_file[self.target_file].matchers:
            if (
                matcher.lnum == lnum
                and matcher.severity == "note"
                and matcher.message.startswith("Revealed type is")
            ):
                found.append(matcher)

        assert len(found) == 1
        found[0].message = found[0].message.replace(remove, "")
        return self

    def parse_content(self, path: str, content: str | None) -> str | None:
        self._build.clear_path(path)

        if content is None:
            return content

        content = textwrap.dedent(content).lstrip()
        result: list[str] = []
        expected = self.on(path)

        lines = content.split("\n")
        # TODO: Clean this up as part of making https://github.com/delfick/pytest-typing-runner
        previous_instruction: _Instruction | None = None
        previous_instruction_line: int | None = None
        for i, line in enumerate(lines):
            m = regexes["instruction"].match(line)
            if m is None:
                if regexes["potential_instruction"].match(line):
                    raise AssertionError(
                        f"Looks like line is trying to be an expectation but it didn't pass the regex for one: {line}"
                    )
                result.append(line)
                previous_instruction = None
                previous_instruction_line = None
                continue

            gd = m.groupdict()
            result.append("")
            previous_instruction_line = expected._parse_instruction(
                i,
                result,
                line,
                prefix_whitespace=gd["prefix_whitespace"],
                instruction=_Instruction(gd["instruction"]),
                options=gd.get("options", "") or "",
                tag=gd.get("tag", "") or "",
                rest=gd["rest"],
                previous_instruction=previous_instruction,
                previous_instruction_line=previous_instruction_line,
            )
            previous_instruction = _Instruction(gd["instruction"])

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
        previous_instruction: _Instruction | None,
        previous_instruction_line: int | None,
    ) -> int:
        if instruction is _Instruction.REVEAL:
            previous_line = result[i - 1]
            m = regexes["assignment"].match(previous_line.strip())
            if m:
                result[i] = f"{prefix_whitespace}reveal_type({m.groupdict()['var_name']})"
                i += 1
            else:
                result[i - 1] = f"{prefix_whitespace}reveal_type({previous_line.strip()})"

            self.add_revealed_type(i, rest, tag=tag)
            return i
        elif instruction is _Instruction.ERROR:
            assert options, "Must use `# ^ ERROR(error-type) ^ error here`"
            if previous_instruction is not None:
                assert previous_instruction_line is not None
                i = previous_instruction_line
            self.add_error(i, options, rest, tag=tag)
            return i
        elif instruction is _Instruction.NOTE:
            self.add_note(i, rest, tag=tag)
            if previous_instruction is not None:
                assert previous_instruction_line is not None
                i = previous_instruction_line
            return i
        elif instruction is _Instruction.TAG:
            assert tag, "Must use a `# ^ TAG[tag-name] ^`"
            assert self.target_file is not None
            self._build.add(self.target_file, i, None, "error", "", tag=tag, tag_only=True)
            return i
        else:
            assert_never(instruction)

    def __iter__(self) -> Iterator[OutputMatcher]:
        if self._build.daemon_should_restart and self._build.for_daemon:
            yield DaemonOutputMatcher(line="Restarting: plugins changed", regex=False)
            yield DaemonOutputMatcher(line="Daemon stopped", regex=False)
        yield from self._build.result
