"""Check the intended source boundary and candidate version metadata.

This is a targeted disclosure check, not a proof that arbitrary secrets are absent.
No matching credential values are printed.
"""

import re
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    paths = (
        subprocess.check_output(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=ROOT
        )
        .decode()
        .split("\0")
    )
    issues = []
    patterns = [
        re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        re.compile(rb"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})"),
        re.compile(rb"sk-(?:proj-|ant-)?[A-Za-z0-9_-]{30,}"),
    ]
    for name in sorted(set(paths) - {""}):
        path = Path(name)
        if (
            any(p in {"runs", ".venv", ".git", "node_modules"} for p in path.parts)
            or (path.name.startswith(".env") and path.name != ".env.example")
            or path.suffix in {".sqlite", ".pem", ".key"}
        ):
            issues.append(f"Excluded source path: {name}")
            continue
        data = (ROOT / path).read_bytes()
        if any(p.search(data) for p in patterns):
            issues.append(f"Possible credential in {name}; inspect privately")
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    if any(" @ " in requirement for requirement in project["dependencies"]):
        issues.append("Core dependencies must not require a private source repository")
    version = re.search(
        r'__version__ = "([^"]+)"', (ROOT / "src/agency_garden/_version.py").read_text()
    ).group(1)
    if f"version: {version}\n" not in (ROOT / "CITATION.cff").read_text():
        issues.append("Citation version differs from package version")
    if f"## {version}" not in (ROOT / "CHANGELOG.md").read_text():
        issues.append("Candidate is missing a changelog entry")
    if issues:
        raise SystemExit("\n".join(issues))
    print(f"Reviewed {len(set(paths) - {''})} source paths; candidate {version}; checks passed")


if __name__ == "__main__":
    main()
