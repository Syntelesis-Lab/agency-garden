"""Transparent scripted baselines and optional, one-request model adapters."""

import importlib
import os
import random
from typing import Any, Literal

from pydantic import Field

from agency_garden.config import StrictModel
from agency_garden.contracts import Decision, Request
from agency_garden.errors import ConfigurationError, PolicyError
from agency_garden.serialization import canonical, clone, parse_json


class Scripted:
    """Choose by menu position or seeded random sampling, without a hidden objective."""

    def __init__(self, strategy: Literal["first", "middle", "last", "random"]) -> None:
        self.strategy = strategy

    def decide(self, request: Request) -> Decision:
        if self.strategy == "random":
            index = random.Random(request.seed).randrange(len(request.actions))
        else:
            index = {
                "first": 0,
                "middle": len(request.actions) // 2,
                "last": len(request.actions) - 1,
            }[self.strategy]
        return Decision(action=clone(request.actions[index]), memory=clone(request.memory))


class ModelParameters(StrictModel):
    model: str = Field(min_length=1, max_length=200)
    max_output_tokens: int = Field(default=1_024, ge=128, le=32_768)
    timeout: float = Field(default=60.0, gt=0, le=600)
    api_key_env: str | None = Field(default=None, pattern=r"^[A-Z][A-Z0-9_]*$")


SYSTEM = (
    "You are one participant in an experimental world. Use only the information in your "
    "observation and memory. Choose exactly one object from the supplied actions menu. "
    "Follow your participant instructions. Return only a JSON object with keys action, "
    "memory, and reason. action must be an unchanged menu object; memory must be a JSON "
    "object for your next turn; reason may be a concise explanation or null. Do not "
    "claim that an action has occurred before the world executes it."
)


class ModelPolicy:
    """Stateless provider calls with explicit carried memory and no automatic retries.

    The response is retained even when it is malformed. A run never substitutes a
    scripted action for a refusal, invalid response, timeout or provider error.
    """

    def __init__(self, provider: Literal["openai", "anthropic"], **parameters: Any) -> None:
        self.provider = provider
        self.parameters = ModelParameters.model_validate(parameters)
        self._client: Any = None

    def check_available(self) -> None:
        name = self.parameters.api_key_env or f"{self.provider.upper()}_API_KEY"
        if not os.environ.get(name):
            raise ConfigurationError(f"Set {name} before running {self.provider} participants")
        try:
            importlib.import_module(self.provider)
        except ImportError as exc:
            raise ConfigurationError(f"Install agency-garden[{self.provider}] first") from exc

    def _get_client(self) -> Any:
        if self._client is None:
            self.check_available()
            module = importlib.import_module(self.provider)
            cls = module.OpenAI if self.provider == "openai" else module.Anthropic
            key_name = self.parameters.api_key_env or f"{self.provider.upper()}_API_KEY"
            self._client = cls(
                api_key=os.environ[key_name], max_retries=0, timeout=self.parameters.timeout
            )
        return self._client

    def decide(self, request: Request) -> Decision:
        client = self._get_client()
        prompt = canonical(request.as_dict())
        p = self.parameters
        try:
            if self.provider == "openai":
                response = client.responses.create(
                    model=p.model,
                    instructions=SYSTEM,
                    input=prompt,
                    max_output_tokens=p.max_output_tokens,
                    store=False,
                )
                text = response.output_text
                status = response.status
                complete = status == "completed"
            else:
                response = client.messages.create(
                    model=p.model,
                    system=SYSTEM,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=p.max_output_tokens,
                )
                text = "".join(block.text for block in response.content if block.type == "text")
                status = response.stop_reason
                complete = status == "end_turn"
        except Exception as exc:
            # Provider exceptions can contain request data; store type and status only.
            raise PolicyError(
                "Provider request failed; its remote outcome may be unknown",
                receipt={
                    "provider": self.provider,
                    "error_type": type(exc).__name__,
                    "status_code": getattr(exc, "status_code", None),
                },
            ) from exc
        receipt = {
            "provider": self.provider,
            "requested_model": p.model,
            "response_model": getattr(response, "model", p.model),
            "response_id": response.id,
            "status": status,
            "text": text,
            "usage": response.usage.model_dump(mode="json") if response.usage else None,
        }
        if not complete:
            raise PolicyError("Provider did not complete a response", receipt=receipt)
        return parse_model_response(text, receipt)


def parse_model_response(text: str, receipt: dict[str, Any]) -> Decision:
    try:
        body = parse_json(text)
        if not isinstance(body, dict) or set(body) != {"action", "memory", "reason"}:
            raise ValueError("Expected exactly action, memory and reason")
        if not isinstance(body["action"], dict) or not isinstance(body["memory"], dict):
            raise ValueError("action and memory must be objects")
        if body["reason"] is not None and not isinstance(body["reason"], str):
            raise ValueError("reason must be a string or null")
        canonical(body)
        return Decision(**body, receipt=receipt)
    except (ValueError, TypeError) as exc:
        raise PolicyError("Model returned invalid decision JSON", receipt=receipt) from exc
