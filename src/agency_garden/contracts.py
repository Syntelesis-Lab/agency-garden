"""Small interfaces for worlds and participants. All persisted values must be JSON."""

from dataclasses import dataclass, field
from typing import Any, Protocol

JSONObject = dict[str, Any]


@dataclass(frozen=True)
class Request:
    """A participant's projected view, never the investigator's complete world state."""

    actor: str
    step: int
    seed: int
    observation: JSONObject
    actions: tuple[JSONObject, ...]
    memory: JSONObject = field(default_factory=dict)
    instructions: str = ""

    def as_dict(self) -> JSONObject:
        return {
            "actor": self.actor,
            "step": self.step,
            "seed": self.seed,
            "observation": self.observation,
            "actions": list(self.actions),
            "memory": self.memory,
            "instructions": self.instructions,
        }


@dataclass(frozen=True)
class Decision:
    action: JSONObject
    memory: JSONObject = field(default_factory=dict)
    reason: str | None = None
    receipt: JSONObject = field(default_factory=dict)

    def as_dict(self) -> JSONObject:
        return {
            "action": self.action,
            "memory": self.memory,
            "reason": self.reason,
            "receipt": self.receipt,
        }


class Policy(Protocol):
    """Return one action from the supplied menu; keep persistent memory explicit."""

    def decide(self, request: Request) -> Decision: ...


class World(Protocol):
    """Pure world transitions. Inputs may be copied; external side effects belong elsewhere."""

    def initial(self, actors: tuple[str, ...], seed: int) -> JSONObject: ...

    def active(self, state: JSONObject) -> tuple[str, ...]: ...

    def observe(self, state: JSONObject, actor: str) -> JSONObject: ...

    def actions(self, state: JSONObject, actor: str) -> tuple[JSONObject, ...]: ...

    def advance(self, state: JSONObject, actions: dict[str, JSONObject]) -> JSONObject: ...

    def finished(self, state: JSONObject) -> bool: ...

    def outcomes(self, state: JSONObject) -> JSONObject: ...
