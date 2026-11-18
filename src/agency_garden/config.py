"""Strict, versioned experiment configuration; JSON and TOML are equivalent inputs."""

import tomllib
from pathlib import Path
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, JsonValue, ValidationError, model_validator

from agency_garden.errors import ConfigurationError
from agency_garden.serialization import parse_json

Identifier = Annotated[str, Field(pattern=r"^[a-zA-Z][a-zA-Z0-9_-]{0,63}$")]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class PolicyConfig(StrictModel):
    kind: Identifier = "random"
    parameters: dict[str, JsonValue] = Field(default_factory=dict)


class AgentConfig(StrictModel):
    id: Identifier
    policy: PolicyConfig = Field(default_factory=PolicyConfig)
    instructions: str = Field(default="", max_length=20_000)


class WorldConfig(StrictModel):
    kind: Identifier = "commons"
    parameters: dict[str, JsonValue] = Field(default_factory=dict)


class Condition(StrictModel):
    """Shallow parameter overrides; omitted values retain the base configuration."""

    name: Identifier
    world: dict[str, JsonValue] = Field(default_factory=dict)
    policies: dict[str, PolicyConfig] = Field(default_factory=dict)


class Limits(StrictModel):
    max_steps: int = Field(default=1_000, ge=1, le=100_000)
    max_decisions: int = Field(default=10_000, ge=1, le=10_000_000)


class Experiment(StrictModel):
    """Conditions × seeds × repetitions, each with a separately initialized state."""

    schema_version: int = Field(default=1, ge=1, le=1)
    name: Identifier
    world: WorldConfig = Field(default_factory=WorldConfig)
    agents: list[AgentConfig] = Field(min_length=1, max_length=64)
    seeds: list[int] = Field(default_factory=lambda: [1], min_length=1, max_length=10_000)
    repetitions: int = Field(default=1, ge=1, le=1_000)
    conditions: list[Condition] = Field(
        default_factory=lambda: [Condition(name="baseline")], min_length=1, max_length=1_000
    )
    limits: Limits = Field(default_factory=Limits)
    description: str = Field(default="", max_length=20_000)

    @model_validator(mode="after")
    def validate_design(self) -> Self:
        ids = [agent.id for agent in self.agents]
        if len(set(ids)) != len(ids):
            raise ValueError("Agent IDs must be unique")
        if len(set(self.seeds)) != len(self.seeds):
            raise ValueError("Seeds must be unique; use repetitions for repeated trials")
        names = [condition.name for condition in self.conditions]
        if len(set(names)) != len(names):
            raise ValueError("Condition names must be unique")
        for condition in self.conditions:
            if set(condition.policies) - set(ids):
                raise ValueError(f"Unknown agent in condition {condition.name!r}")
        if len(self.conditions) * len(self.seeds) * self.repetitions > 100_000:
            raise ValueError("An experiment may contain at most 100,000 episodes")
        return self


def load_experiment(path: str | Path) -> Experiment:
    source = Path(path)
    try:
        text = source.read_text(encoding="utf-8")
        data = tomllib.loads(text) if source.suffix == ".toml" else parse_json(text)
        return Experiment.model_validate(data)
    except (OSError, ValueError, ValidationError) as exc:
        raise ConfigurationError(f"Cannot load {source}: {exc}") from exc
