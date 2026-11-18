import importlib.util
import subprocess
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "publish_ref", Path(__file__).resolve().parents[1] / "scripts/check_publish_ref.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.fixture
def release_repo(tmp_path):
    def git(*args):
        return subprocess.check_output(["git", "-C", str(tmp_path), *args], text=True).strip()

    git("init", "-q")
    git("config", "user.name", "Release test")
    git("config", "user.email", "test@example.invalid")
    git("commit", "--allow-empty", "-qm", "Original candidate")
    sha = git("rev-parse", "HEAD")
    git("tag", "v0.1.0a2")
    return tmp_path, sha, git


def test_approved_tag_resolves_to_immutable_commit(release_repo):
    directory, sha, _ = release_repo
    assert module.resolve_release("v0.1.0a2", sha, directory) == sha


def test_moved_tag_is_rejected(release_repo):
    directory, sha, git = release_repo
    git("commit", "--allow-empty", "-qm", "Different source")
    git("tag", "-f", "v0.1.0a2")
    with pytest.raises(ValueError, match="approved commit"):
        module.resolve_release("v0.1.0a2", sha, directory)


@pytest.mark.parametrize("tag", ["main", "HEAD", "--help", "v0.1.0a2^{commit}"])
def test_branch_or_expression_cannot_stand_in_for_release_tag(release_repo, tag):
    directory, sha, _ = release_repo
    with pytest.raises(ValueError, match="version tag"):
        module.resolve_release(tag, sha, directory)


def test_unapproved_commit_fails(release_repo):
    directory, _, _ = release_repo
    with pytest.raises(ValueError, match="explicitly identify"):
        module.resolve_release("v0.1.0a2", "", directory)


@pytest.mark.parametrize(
    "override",
    [
        {"REPOSITORY_PRIVATE": "true"},
        {"PUBLISH_ENABLED": "false"},
        {"GITHUB_REF": "refs/heads/feature"},
    ],
)
def test_disabled_context_fails_before_resolving_or_publishing(monkeypatch, override):
    for key, value in {
        "REPOSITORY_PRIVATE": "false",
        "PUBLISH_ENABLED": "true",
        "GITHUB_REF": "refs/heads/main",
        **override,
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(module, "resolve_release", lambda *a: pytest.fail("Gate was bypassed"))
    with pytest.raises(ValueError):
        module.main()
