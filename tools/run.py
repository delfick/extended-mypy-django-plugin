import os
import pathlib
import shutil
import subprocess
import sys

import click

here = pathlib.Path(__file__).parent


def run(*args: str, old: bool) -> None:
    if old:
        withs = ["--package", "tools", "--extra", "old-django"]
    else:
        withs = ["--package", "tools", "--extra", "new-django"]

    try:
        subprocess.run(["/bin/bash", str(here / "uv"), "run", *withs, *args], check=True)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)


@click.group()
def cli() -> None:
    pass


@cli.command(context_settings=dict(ignore_unknown_options=True))
@click.option("--old", is_flag=True)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def docs(args: list[str], old: bool) -> None:
    docs_path = here / ".." / "docs"
    build_path = docs_path / "_build"
    cmd: list[pathlib.Path | str] = ["python", "-m", "sphinx.cmd.build"]

    other_args: list[str] = []
    for arg in args:
        if arg == "fresh":
            if build_path.exists():
                shutil.rmtree(build_path)
        elif arg == "view":
            cmd = ["python", "-m", "sphinx_autobuild", "--port", "9876"]
        else:
            other_args.append(arg)

    os.chdir(docs_path)

    (build_path / "html").mkdir(exist_ok=True, parents=True)
    (build_path / "doctrees").mkdir(exist_ok=True, parents=True)

    run(
        "--package",
        "tools",
        "--extra",
        "docs",
        *(str(c) for c in cmd),
        ".",
        "_build/html",
        "-b",
        "html",
        "-d",
        "_build/doctrees",
        *other_args,
        old=old,
    )


@cli.command(context_settings=dict(ignore_unknown_options=True))
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def format(args: list[str]) -> None:
    """
    Run ruff format and ruff check fixing I and UP rules
    """
    if not args:
        args = [".", *args]
    subprocess.run([sys.executable, "-m", "ruff", "format", *args], check=True)
    subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--fix", "--select", "I,UP", *args],
        check=True,
    )


@cli.command(context_settings=dict(ignore_unknown_options=True))
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def lint(args: list[str]) -> None:
    """
    Run ruff check
    """
    os.execv(sys.executable, [sys.executable, "-m", "ruff", "check", *args])


@cli.command(context_settings=dict(ignore_unknown_options=True))
@click.option("--old", is_flag=True)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def types(args: list[str], old: bool) -> None:
    """
    Run mypy
    """
    specified: bool = True
    locations: list[str] = [a for a in args if not a.startswith("-")]
    args = [a for a in args if a.startswith("-")]

    if not locations:
        specified = False
        locations.append(str((here / "..").resolve()))
    else:
        cwd = pathlib.Path.cwd()
        paths: list[pathlib.Path] = []
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

    run("python", "-m", "mypy", *locations, *args, "--enable-incomplete-feature=Unpack", old=old)

    if not specified:
        run(
            "python",
            "-m",
            "mypy",
            str(here.parent / "example"),
            "--config-file",
            str(here.parent / "example" / "mypy.ini"),
            *args,
            old=old,
        )


@cli.command(context_settings=dict(ignore_unknown_options=True))
@click.option("--old", is_flag=True)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def tests(args: list[str], old: bool) -> None:
    """
    Run pytest
    """
    run("python", "-m", "pytest", *args, old=old)


if __name__ == "__main__":
    cli()
