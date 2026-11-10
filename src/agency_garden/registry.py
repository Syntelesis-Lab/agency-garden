"""Explicit local extensions with versioned, file-backed implementation identities."""

import hashlib
import importlib.metadata
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Any, Generic, Literal, TypeVar

from agency_garden.contracts import Policy, World
from agency_garden.errors import ConfigurationError
from agency_garden.policies import ModelPolicy, Scripted
from agency_garden.worlds import Commons, Trust

T = TypeVar("T")


@dataclass(frozen=True)
class Extension(Generic[T]):
    factory: Callable[..., T]
    version: str
    files: tuple[Path, ...]
    dependencies: tuple[str, ...]

    def identity(self) -> dict[str, Any]:
        names = [path.name for path in self.files]
        if len(set(names)) != len(names):
            raise ConfigurationError("Extension source files must have distinct basenames")
        try:
            return {
                "version": self.version,
                "files": {
                    path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in sorted(self.files)
                },
                "dependencies": {
                    name: importlib.metadata.version(name) for name in self.dependencies
                },
            }
        except (OSError, importlib.metadata.PackageNotFoundError) as exc:
            raise ConfigurationError(f"Cannot identify extension: {exc}") from exc


class Registry:
    """Register trusted Python factories. Declared source and dependencies are frozen per run."""

    def __init__(self) -> None:
        self.worlds: dict[str, Extension[World]] = {}
        self.policies: dict[str, Extension[Policy]] = {}

    def register_world(
        self,
        name: str,
        factory: Callable[..., World],
        *,
        version: str,
        files: Iterable[str | Path],
        dependencies: Iterable[str] = (),
    ) -> None:
        self._register(self.worlds, name, factory, version, files, dependencies)

    def register_policy(
        self,
        name: str,
        factory: Callable[..., Policy],
        *,
        version: str,
        files: Iterable[str | Path],
        dependencies: Iterable[str] = (),
    ) -> None:
        self._register(self.policies, name, factory, version, files, dependencies)

    @staticmethod
    def _register(
        table: dict[str, Extension[T]],
        name: str,
        factory: Callable[..., T],
        version: str,
        files: Iterable[str | Path],
        dependencies: Iterable[str],
    ) -> None:
        if name in table:
            raise ConfigurationError(f"Extension {name!r} is already registered")
        paths = tuple(Path(p).resolve() for p in files)
        if not paths or not version:
            raise ConfigurationError("Extensions require a version and at least one source file")
        table[name] = Extension(factory, version, paths, tuple(dependencies))

    def world(self, name: str, parameters: dict[str, Any]) -> World:
        if name not in self.worlds:
            raise ConfigurationError(f"Unknown world {name!r}; available: {', '.join(self.worlds)}")
        return self.worlds[name].factory(**parameters)

    def policy(self, name: str, parameters: dict[str, Any]) -> Policy:
        if name not in self.policies:
            raise ConfigurationError(
                f"Unknown policy {name!r}; available: {', '.join(self.policies)}"
            )
        return self.policies[name].factory(**parameters)


def _scripted_factory(
    strategy: Literal["first", "middle", "last", "random"], /, **parameters: Any
) -> Policy:
    if parameters:
        raise ConfigurationError("Scripted policies do not accept parameters")
    return Scripted(strategy)


def _model_factory(provider: Literal["openai", "anthropic"], /, **parameters: Any) -> Policy:
    return ModelPolicy(provider, **parameters)


def default_registry() -> Registry:
    registry = Registry()
    source = Path(__file__).parent
    registry.register_world("commons", Commons, version="1", files=[source / "worlds/commons.py"])
    registry.register_world("trust", Trust, version="1", files=[source / "worlds/trust.py"])
    for name in ("first", "middle", "last", "random"):
        registry.register_policy(
            name, partial(_scripted_factory, name), version="1", files=[source / "policies.py"]
        )
    providers: tuple[Literal["openai", "anthropic"], ...] = ("openai", "anthropic")
    for provider in providers:
        registry.register_policy(
            provider,
            partial(_model_factory, provider),
            version="1",
            files=[source / "policies.py"],
            dependencies=[provider],
        )
    return registry


def package_identity() -> dict[str, Any]:
    root = Path(__file__).parent
    return {
        "files": {
            str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.rglob("*.py"))
        },
        "dependencies": {
            name: importlib.metadata.version(name) for name in ("pydantic", "filelock")
        },
    }
