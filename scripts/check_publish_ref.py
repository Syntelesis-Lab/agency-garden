"""Resolve an explicitly approved existing release tag once, without publishing."""

import os
import re
import subprocess
from pathlib import Path


def resolve_release(tag: str, approved_commit: str, directory: Path) -> str:
    if not re.fullmatch(r"v\d+\.\d+\.\d+(?:(?:a|b|rc)\d+)?", tag):
        raise ValueError("Supply an existing version tag, not a branch or expression")
    if not re.fullmatch(r"[0-9a-f]{40}", approved_commit):
        raise ValueError("PYPI_APPROVED_COMMIT must explicitly identify one source commit")
    commit = subprocess.check_output(
        ["git", "rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}"],
        cwd=directory,
        text=True,
    ).strip()
    if commit != approved_commit:
        raise ValueError("Release tag does not identify the approved commit")
    return commit


def main() -> None:
    if os.environ.get("REPOSITORY_PRIVATE") != "false":
        raise ValueError("Publication is disabled while the repository is private")
    if os.environ.get("PUBLISH_ENABLED") != "true":
        raise ValueError("Publication has not been explicitly enabled")
    if os.environ.get("GITHUB_REF") != "refs/heads/main":
        raise ValueError("Dispatch publication only from main")
    commit = resolve_release(
        os.environ.get("RELEASE_TAG", ""),
        os.environ.get("APPROVED_COMMIT", ""),
        Path.cwd(),
    )
    with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as stream:
        stream.write(f"commit={commit}\n")
    print(f"Validated release source: {commit}")


if __name__ == "__main__":
    main()
