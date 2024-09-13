import inspect
import os
import shlex
import shutil
import sys
import typing as tp
from collections.abc import Callable
from pathlib import Path

here = Path(__file__).parent


class Command:
    __is_command__: bool

    def __call__(self, bin_dir: Path, args: list[str]) -> None: ...


def command(func: Callable[..., None]) -> Callable[..., None]:
    tp.cast(Command, func).__is_command__ = True
    return func


def run(*args: str | Path) -> None:
    cmd = " ".join(shlex.quote(str(part)) for part in args)
    print(f"Running '{cmd}'\n")  # noqa: T201
    ret = os.system(cmd)
    if ret != 0:
        sys.exit(1)


class App:
    commands: dict[str, Command]

    def __init__(self) -> None:
        self.commands = {}

        compare = inspect.signature(type("C", (Command,), {})().__call__)

        for name in dir(self):
            val = getattr(self, name)
            if getattr(val, "__is_command__", False):
                assert (
                    inspect.signature(val) == compare
                ), f"Expected '{name}' to have correct signature, have {inspect.signature(val)} instead of {compare}"
                self.commands[name] = val

    def __call__(self, args: list[str]) -> None:
        bin_dir = Path(sys.executable).parent

        if args and args[0] in self.commands:
            os.chdir(here.parent)
            self.commands[args[0]](bin_dir, args[1:])
            return

        sys.exit(f"Unknown command:\nAvailable: {sorted(self.commands)}\nWanted: {args}")

    @command
    def lint(self, bin_dir: Path, args: list[str]) -> None:
        run(bin_dir / "ruff", "check", *args)

    @command
    def format(self, bin_dir: Path, args: list[str]) -> None:
        if not args:
            args = [".", *args]
        run(bin_dir / "ruff", "format", *args)
        run(bin_dir / "ruff", "check", "--fix", "--select", "I,UP", *args)

    @command
    def types(self, bin_dir: Path, args: list[str]) -> None:
        specified: bool = True
        locations: list[str] = [a for a in args if not a.startswith("-")]
        args = [a for a in args if a.startswith("-")]

        if not locations:
            specified = False
            locations.append(str((here / "..").resolve()))
        else:
            cwd = Path.cwd()
            paths: list[Path] = []
            for location in locations:
                from_current = cwd / location
                from_root = here.parent / location

                if from_current.exists():
                    paths.append(from_current)
                elif from_root.exists():
                    paths.append(from_root)
                else:
                    raise ValueError(f"Couldn't find path for {location}")

            example_root = here.parent / "example"
            if any(path.is_relative_to(example_root) for path in paths):
                if not all(path.is_relative_to(example_root) for path in paths):
                    raise ValueError("If specifying an example path, all paths must be from there")
                os.chdir(example_root)
            locations = [str(path) for path in paths]

        run(bin_dir / "mypy", *locations, *args, "--enable-incomplete-feature=Unpack")

        if not specified:
            os.chdir(here.parent / "example")
            run(bin_dir / "mypy", ".", *args)

    @command
    def tests(self, bin_dir: Path, args: list[str]) -> None:
        run(bin_dir / "pytest", *args)

    @command
    def docs(self, bin_dir: Path, args: list[str]) -> None:
        docs_path = here / ".." / "docs"
        build_path = docs_path / "_build"
        command: list[Path | str] = [bin_dir / "sphinx-build"]

        other_args: list[str] = []
        for arg in args:
            if arg == "fresh":
                if build_path.exists():
                    shutil.rmtree(build_path)
            elif arg == "view":
                command = [bin_dir / "sphinx-autobuild", "--port", "9876"]
            else:
                other_args.append(arg)

        (build_path / "html").mkdir(exist_ok=True, parents=True)
        (build_path / "doctrees").mkdir(exist_ok=True, parents=True)

        os.chdir(docs_path)

        run(*command, ".", "_build/html", "-b", "html", "-d", "_build/doctrees", *other_args)


app = App()

if __name__ == "__main__":
    app(sys.argv[1:])
