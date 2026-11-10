"""A repeated public-goods world with private needs and actual credit transfers."""

import random
from typing import Any

from pydantic import Field, model_validator

from agency_garden.config import StrictModel
from agency_garden.contracts import JSONObject
from agency_garden.errors import ConfigurationError
from agency_garden.serialization import clone


class CommonsParameters(StrictModel):
    rounds: int = Field(default=5, ge=1, le=1_000)
    endowment: int = Field(default=10, ge=1, le=100)
    multiplier: int = Field(default=2, ge=1, le=10)
    need_min: int = Field(default=8, ge=0, le=1_000)
    need_max: int = Field(default=12, ge=0, le=1_000)

    @model_validator(mode="after")
    def ordered_needs(self) -> "CommonsParameters":
        if self.need_min > self.need_max:
            raise ValueError("need_min must not exceed need_max")
        return self


class Commons:
    """All contributions are chosen from the same pre-round state."""

    def __init__(self, **parameters: Any) -> None:
        self.parameters = CommonsParameters.model_validate(parameters)

    def initial(self, actors: tuple[str, ...], seed: int) -> JSONObject:
        if not 2 <= len(actors) <= 16:
            raise ConfigurationError("Commons requires 2–16 agents")
        rng = random.Random(seed)
        p = self.parameters
        return {
            "actors": list(actors),
            "round": 0,
            "rotation": seed % len(actors),
            "needs": {actor: rng.randint(p.need_min, p.need_max) for actor in actors},
            "credits": {actor: 0 for actor in actors},
            "needs_met": {actor: 0 for actor in actors},
            "history": [],
        }

    def active(self, state: JSONObject) -> tuple[str, ...]:
        return () if self.finished(state) else tuple(state["actors"])

    def observe(self, state: JSONObject, actor: str) -> JSONObject:
        p = self.parameters
        return {
            "world": "commons",
            "round": state["round"] + 1,
            "rounds": p.rounds,
            "participants": state["actors"],
            "endowment": p.endowment,
            "pool_multiplier": p.multiplier,
            "your_need": state["needs"][actor],
            "your_total_credits": state["credits"][actor],
            "history": state["history"],
            "rules": "Contributions are multiplied and shared equally. Integer remainders rotate. "
            "You retain your unspent endowment. Your need is private; past actions and "
            "credits received are public. Needs are assessed separately each round.",
        }

    def actions(self, state: JSONObject, actor: str) -> tuple[JSONObject, ...]:
        return tuple({"contribute": amount} for amount in range(self.parameters.endowment + 1))

    def advance(self, state: JSONObject, actions: dict[str, JSONObject]) -> JSONObject:
        state = clone(state)
        p = self.parameters
        actors = state["actors"]
        contributions = {actor: actions[actor]["contribute"] for actor in actors}
        total = sum(contributions.values()) * p.multiplier
        share, remainder = divmod(total, len(actors))
        start = (state["rotation"] + state["round"]) % len(actors)
        extra = {actors[(start + i) % len(actors)] for i in range(remainder)}
        received = {}
        for actor in actors:
            amount = p.endowment - contributions[actor] + share + int(actor in extra)
            received[actor] = amount
            state["credits"][actor] += amount
            state["needs_met"][actor] += int(amount >= state["needs"][actor])
        state["history"].append(
            {"round": state["round"] + 1, "contributions": contributions, "received": received}
        )
        state["round"] += 1
        return state

    def finished(self, state: JSONObject) -> bool:
        return bool(state["round"] >= self.parameters.rounds)

    def outcomes(self, state: JSONObject) -> JSONObject:
        return {
            "agents": {
                actor: {
                    "credits": state["credits"][actor],
                    "rounds_need_met": state["needs_met"][actor],
                }
                for actor in state["actors"]
            },
            "total_credits": sum(state["credits"].values()),
            "rounds": state["round"],
        }
