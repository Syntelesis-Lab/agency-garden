"""A small CLI that works from an installed wheel, outside a source checkout."""

import argparse
import importlib.util
import json
import os
import shlex
import sqlite3
import subprocess
import sys
import webbrowser
from contextlib import suppress
from importlib.resources import files
from pathlib import Path

from pydantic import ValidationError

from agency_garden._version import __version__
from agency_garden.config import Experiment, load_experiment
from agency_garden.errors import ConfigurationError, GardenError
from agency_garden.registry import Registry, default_registry
from agency_garden.report import read_run, write_report
from agency_garden.runtime import run, specification
from agency_garden.serialization import digest, write_json
from agency_garden.store import RunStore


def _registry(paths: list[str]) -> Registry:
    registry = default_registry()
    for path in paths:
        source = Path(path).resolve()
        if not source.is_file() or source.suffix != ".py":
            raise ConfigurationError(f"Plugin must be an existing Python file: {source}")
        name = "agency_garden_plugin_" + digest(str(source))[:12]
        spec = importlib.util.spec_from_file_location(name, source)
        if not spec or not spec.loader:
            raise ConfigurationError(f"Cannot load plugin {source}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        if not callable(getattr(module, "register", None)):
            raise ConfigurationError("Plugin must expose register(registry)")
        module.register(registry)
    return registry


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agency-garden", description="Build worlds. Investigate agency."
    )
    parser.add_argument("--version", action="version", version=f"Agency Garden {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="Create an offline, editable experiment")
    init.add_argument("world", choices=["commons", "trust", "custom"])
    init.add_argument("directory", type=Path)
    for name in ("plan", "run"):
        sub = commands.add_parser(
            name, help="Validate an experiment" if name == "plan" else "Run an experiment"
        )
        sub.add_argument("experiment", type=Path)
        sub.add_argument(
            "--plugin-file", action="append", default=[], help="Execute this trusted local plugin"
        )
        if name == "run":
            sub.add_argument("--output", type=Path, required=True)
    resume = commands.add_parser("resume", help="Resume the exact recorded configuration")
    resume.add_argument("directory", type=Path)
    resume.add_argument("--plugin-file", action="append", default=[])
    resume.add_argument(
        "--retry-failed",
        action="store_true",
        help="Explicitly retry failed/uncertain calls; may duplicate remote work or charges",
    )
    for name in ("report", "view", "verify"):
        sub = commands.add_parser(
            name,
            help={
                "report": "Write JSON and HTML summaries",
                "view": "Open the offline run explorer",
                "verify": "Verify the event journal and current records",
            }[name],
        )
        sub.add_argument("directory", type=Path)
        if name != "verify":
            sub.add_argument("--include-private", action="store_true")
    schema = commands.add_parser("schema", help="Print the experiment JSON schema")
    schema.add_argument("--output", type=Path)
    commands.add_parser("list", help="List built-in worlds and policies")
    return parser


def _init(world: str, directory: Path) -> None:
    if directory.exists() and (not directory.is_dir() or any(directory.iterdir())):
        raise ConfigurationError(
            "Choose a new or empty directory; init never overwrites existing work"
        )
    directory.mkdir(parents=True, exist_ok=True)
    templates = files("agency_garden").joinpath("templates")
    (directory / "experiment.toml").write_text(
        templates.joinpath(f"{world}.toml").read_text(encoding="utf-8"), encoding="utf-8"
    )
    if world == "custom":
        (directory / "world.py").write_text(
            templates.joinpath("custom_world.py.txt").read_text(encoding="utf-8"), encoding="utf-8"
        )
    print(f"Created {directory / 'experiment.toml'}")
    command = [
        "agency-garden",
        "run",
        str(directory / "experiment.toml"),
        "--output",
        str(directory / "run"),
    ]
    if world == "custom":
        command.extend(["--plugin-file", str(directory / "world.py")])
    rendered = subprocess.list2cmdline(command) if os.name == "nt" else shlex.join(command)
    print(f"Next: {rendered}")


def _execute(args: argparse.Namespace) -> None:
    if args.command == "init":
        _init(args.world, args.directory)
    elif args.command == "list":
        registry = default_registry()
        print("Worlds: " + ", ".join(registry.worlds))
        print("Policies: " + ", ".join(registry.policies))
    elif args.command == "schema":
        schema = Experiment.model_json_schema()
        if args.output:
            write_json(args.output, schema)
        else:
            print(json.dumps(schema, indent=2))
    elif args.command in {"plan", "run", "resume"}:
        registry = _registry(args.plugin_file)
        if args.command == "resume":
            with RunStore(args.directory / "run.sqlite", read_only=True) as store:
                store.verify()
                manifest = store.get("manifest", "run")
            if not manifest:
                raise ConfigurationError("Run has no manifest")
            experiment = Experiment.model_validate(manifest["specification"]["experiment"])
            output, retry = args.directory, args.retry_failed
        else:
            experiment = load_experiment(args.experiment)
            output, retry = getattr(args, "output", None), False
        if args.command == "plan":
            spec = specification(experiment, registry)
            print(
                json.dumps(
                    {
                        "name": experiment.name,
                        "fingerprint": digest(spec),
                        "episodes": len(experiment.conditions)
                        * len(experiment.seeds)
                        * experiment.repetitions,
                        "limits": experiment.limits.model_dump(),
                        "provider_calls": 0,
                    },
                    indent=2,
                )
            )
            return
        try:
            result = run(experiment, output, registry=registry, retry_failed=retry)
        except GardenError:
            if (output / "run.sqlite").is_file():
                with suppress(GardenError, sqlite3.Error):
                    write_report(output)
            raise
        _, page = write_report(result.directory)
        print(
            f"Completed {result.completed}/{result.episodes} episodes; "
            f"{result.attempts} decision attempts."
        )
        print(f"Report: {page}")
    elif args.command == "verify":
        data = read_run(args.directory)
        print(json.dumps(data["integrity"], indent=2))
    else:
        report, page = write_report(args.directory, include_private=args.include_private)
        print(f"JSON: {report}\nHTML: {page}")
        if args.command == "view":
            webbrowser.open(page.resolve().as_uri())


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        _execute(args)
        return 0
    except (GardenError, ValidationError, OSError, sqlite3.Error, ValueError) as exc:
        print(f"agency-garden: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print(
            "Interrupted. Saved decisions remain available; inspect the run before resuming.",
            file=sys.stderr,
        )
        return 130
