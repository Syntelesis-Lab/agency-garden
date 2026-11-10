"""A repeated, sequential investment game with visible transfer consequences."""

from typing import Any

from pydantic import Field

from agency_garden.config import StrictModel
from agency_garden.contracts import JSONObject
from agency_garden.errors import ConfigurationError
from agency_garden.serialization import clone


class TrustParameters(StrictModel):
    rounds: int = Field(default=5, ge=1, le=1_000)
    endowment: int = Field(default=10, ge=1, le=100)
    multiplier: int = Field(default=3, ge=1, le=10)


class Trust:
    """Roles alternate by round; the recipient can return any received amount."""

    def __init__(self, **parameters: Any) -> None:
        self.parameters = TrustParameters.model_validate(parameters)

    def initial(self, actors: tuple[str, ...], seed: int) -> JSONObject:
        if len(actors) != 2:
            raise ConfigurationError("Trust requires exactly two agents")
        return {
            "actors": list(actors),
            "round": 0,
            "phase": "send",
            "sent": 0,
            "first": seed % 2,
            "credits": dict.fromkeys(actors, 0),
            "history": [],
        }

    def _roles(self, state: JSONObject) -> tuple[str, str]:
        first = (state["first"] + state["round"]) % 2
        return state["actors"][first], state["actors"][1 - first]

    def active(self, state: JSONObject) -> tuple[str, ...]:
        if self.finished(state):
            return ()
        sender, recipient = self._roles(state)
        return (sender if state["phase"] == "send" else recipient,)

    def observe(self, state: JSONObject, actor: str) -> JSONObject:
        sender, recipient = self._roles(state)
        return {
            "world": "trust",
            "round": state["round"] + 1,
            "rounds": self.parameters.rounds,
            "phase": state["phase"],
            "sender": sender,
            "recipient": recipient,
            "endowment": self.parameters.endowment,
            "multiplier": self.parameters.multiplier,
            "sent": state["sent"],
            "received": state["sent"] * self.parameters.multiplier,
            "credits": state["credits"],
            "history": state["history"],
            "rules": "Both receive a fresh endowment each round. The sender transfers any "
            "part of it. The transfer is multiplied; the recipient may return any "
            "part of that received transfer. Roles alternate each round.",
        }

    def actions(self, state: JSONObject, actor: str) -> tuple[JSONObject, ...]:
        if state["phase"] == "send":
            return tuple({"send": n} for n in range(self.parameters.endowment + 1))
        return tuple({"return": n} for n in range(state["sent"] * self.parameters.multiplier + 1))

    def advance(self, state: JSONObject, actions: dict[str, JSONObject]) -> JSONObject:
        state = clone(state)
        sender, recipient = self._roles(state)
        if state["phase"] == "send":
            state["sent"] = actions[sender]["send"]
            state["phase"] = "return"
        else:
            sent, returned = state["sent"], actions[recipient]["return"]
            state["credits"][sender] += self.parameters.endowment - sent + returned
            state["credits"][recipient] += (
                self.parameters.endowment + sent * self.parameters.multiplier - returned
            )
            state["history"].append(
                {
                    "round": state["round"] + 1,
                    "sender": sender,
                    "recipient": recipient,
                    "sent": sent,
                    "returned": returned,
                }
            )
            state.update(round=state["round"] + 1, phase="send", sent=0)
        return state

    def finished(self, state: JSONObject) -> bool:
        return bool(state["round"] >= self.parameters.rounds)

    def outcomes(self, state: JSONObject) -> JSONObject:
        return {
            "agents": {actor: {"credits": amount} for actor, amount in state["credits"].items()},
            "total_sent": sum(row["sent"] for row in state["history"]),
            "total_returned": sum(row["returned"] for row in state["history"]),
            "rounds": state["round"],
        }
