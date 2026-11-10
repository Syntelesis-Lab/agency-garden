"""Install a built wheel in isolation and exercise every packaged tutorial.

Usage: python scripts/verify_distribution.py dist/package.whl [--sdist dist/package.tar.gz]
No model requests are made. Installing build/runtime dependencies may use the network.
"""

import argparse
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import venv
import zipfile
from pathlib import Path


def command(args: list[str], directory: Path, env: dict[str, str]) -> str:
    result = subprocess.run(
        args, cwd=directory, env=env, check=True, text=True, capture_output=True
    )
    return result.stdout


def verify(wheel: Path, root: Path) -> None:
    env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    env["PYTHONNOUSERSITE"] = "1"
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        assert "agency_garden/py.typed" in names
        assert "agency_garden/templates/report.html" in names
        assert not any(name.startswith(("tests/", "docs/", "examples/")) for name in names)
    environment = root / "environment"
    venv.EnvBuilder(with_pip=True).create(environment)
    binary = environment / ("Scripts" if os.name == "nt" else "bin")
    python = str(binary / ("python.exe" if os.name == "nt" else "python"))
    cli = str(binary / ("agency-garden.exe" if os.name == "nt" else "agency-garden"))
    try:
        command([python, "-m", "pip", "install", str(wheel)], root, env)
        command([python, "-m", "pip", "check"], root, env)
        probe = command(
            [
                python,
                "-c",
                "import agency_garden, importlib.util; "
                "assert importlib.util.find_spec('openai') is None; "
                "assert importlib.util.find_spec('anthropic') is None; "
                "print(agency_garden.__file__)",
            ],
            root,
            env,
        ).strip()
        assert environment.resolve() in Path(probe).resolve().parents, probe
        print(command([cli, "--version"], root, env).strip())
        command([python, "-m", "agency_garden", "list"], root, env)
        for name, expected_decisions in (("commons", 120), ("trust", 60), ("custom", 60)):
            # A path with spaces catches accidental shell splitting in examples or tooling.
            study = root / f"{name} study"
            output = study / "run"
            command([cli, "init", name, str(study)], root, env)
            plugin = ["--plugin-file", str(study / "world.py")] if name == "custom" else []
            config = str(study / "experiment.toml")
            plan = json.loads(command([cli, "plan", config, *plugin], root, env))
            assert plan["episodes"] == 6 and plan["provider_calls"] == 0
            command([cli, "run", config, "--output", str(output), *plugin], root, env)
            before = json.loads((output / "report.json").read_text(encoding="utf-8"))
            assert before["completed"] == before["planned"] == 6
            assert before["attempts"] == expected_decisions
            command([cli, "resume", str(output), *plugin], root, env)
            after = json.loads((output / "report.json").read_text(encoding="utf-8"))
            assert after == before, "Completed resume must not change evidence"
            command([cli, "verify", str(output)], root, env)
            command([cli, "report", str(output), "--include-private"], root, env)
            private = json.loads((output / "report.private.json").read_text(encoding="utf-8"))
            assert private["includes_private"]
            assert "state" not in before["episodes"][0]
            assert "state" in private["episodes"][0]
            assert (output / "report.html").is_file()
            print(f"  {name}: 6 episodes, {expected_decisions} decisions, resume verified")
    except subprocess.CalledProcessError as exc:
        print(exc.stdout, file=sys.stderr)
        print(exc.stderr, file=sys.stderr)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    parser.add_argument("--sdist", type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="agency-garden-install-") as temporary:
        root = Path(temporary)
        verify(args.wheel.resolve(), root / "wheel")
        if args.sdist:
            source = root / "source"
            source.mkdir()
            with tarfile.open(args.sdist.resolve()) as archive:
                archive.extractall(source, filter="data")
            projects = list(source.iterdir())
            assert len(projects) == 1 and (projects[0] / "pyproject.toml").is_file()
            rebuilt = root / "rebuilt"
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "build",
                    "--wheel",
                    "--outdir",
                    str(rebuilt),
                    str(projects[0]),
                ],
                check=True,
            )
            wheels = list(rebuilt.glob("*.whl"))
            assert len(wheels) == 1
            verify(wheels[0], root / "sdist-wheel")
    print("Distribution verification passed.")


if __name__ == "__main__":
    main()
