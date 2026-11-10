"""Execute a frozen experiment with sealed observations and explicit recovery."""

import hashlib
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from filelock import FileLock, Timeout

from agency_garden._version import __version__
from agency_garden.config import AgentConfig, Condition, Experiment
from agency_garden.contracts import Decision, JSONObject, Policy, Request, World
from agency_garden.errors import ConfigurationError, IntegrityError, PolicyError, RunBlocked
from agency_garden.policies import ModelPolicy
from agency_garden.registry import Registry, default_registry, package_identity
from agency_garden.serialization import canonical, clone, digest, write_json
from agency_garden.store import RunStore


@dataclass(frozen=True)
class RunResult:
    directory: Path
    fingerprint: str
    completed: int
    episodes: int
    attempts: int


def _policies(
    experiment: Experiment, condition: Condition, registry: Registry
) -> dict[str, Policy]:
    return {
        agent.id: registry.policy(
            (config := condition.policies.get(agent.id, agent.policy)).kind,
            clone(config.parameters),
        )
        for agent in experiment.agents
    }


def specification(experiment: Experiment, registry: Registry) -> JSONObject:
    """Validate all conditions and freeze every used implementation before execution."""
    actors = tuple(agent.id for agent in experiment.agents)
    used_policies: set[str] = set()
    for condition in experiment.conditions:
        parameters = {**experiment.world.parameters, **condition.world}
        world = registry.world(experiment.world.kind, clone(parameters))
        canonical(world.initial(actors, experiment.seeds[0]))
        _policies(experiment, condition, registry)
        used_policies.update(condition.policies.get(a.id, a.policy).kind for a in experiment.agents)
    return {
        "schema_version": 1,
        "engine_version": __version__,
        "python": platform.python_version(),
        "experiment": experiment.model_dump(mode="json"),
        "engine": package_identity(),
        "world": registry.worlds[experiment.world.kind].identity(),
        "policies": {name: registry.policies[name].identity() for name in sorted(used_policies)},
    }


def _request_seed(seed: int, repetition: int, step: int, actor: str) -> int:
    # Omit condition so scripted random choices can be paired across interventions.
    raw = canonical([seed, repetition, step, actor]).encode()
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], "big")


def _validate_decision(decision: Decision, request: Request) -> JSONObject:
    if not isinstance(decision, Decision):
        raise PolicyError("Policy must return a Decision")
    if canonical(decision.action) not in {canonical(action) for action in request.actions}:
        raise PolicyError("Policy returned an action outside its menu", receipt=decision.as_dict())
    if not isinstance(decision.memory, dict) or len(canonical(decision.memory)) > 65_536:
        raise PolicyError(
            "Participant memory must be an object of at most 65,536 characters",
            receipt=decision.as_dict(),
        )
    if decision.reason is not None and (
        not isinstance(decision.reason, str) or len(decision.reason) > 8_192
    ):
        raise PolicyError(
            "Reason must be null or a string of at most 8,192 characters",
            receipt=decision.as_dict(),
        )
    return cast(JSONObject, clone(decision.as_dict()))


def _choose(
    store: RunStore,
    episode: str,
    request: Request,
    policy: Policy,
    *,
    retry_failed: bool,
    limit: int,
) -> JSONObject:
    key = f"{episode}:{request.step:06d}:{request.actor}"
    packet = clone(request.as_dict())
    previous = store.get("decision", key)
    if previous:
        if previous["request"] != packet:
            raise IntegrityError("Reconstructed participant request differs from the saved request")
        if previous["status"] == "completed":
            return previous["decision"]  # type: ignore[no-any-return]
        if not retry_failed:
            raise RunBlocked(
                f"Decision {key} is {previous['status']}. Inspect it, then use "
                "resume --retry-failed only if another attempt is intended."
            )
    if store.attempts() >= limit:
        raise RunBlocked(f"The run reached its {limit} decision-attempt limit")
    record = {
        "episode": episode,
        "step": request.step,
        "actor": request.actor,
        "attempt": previous["attempt"] + 1 if previous else 1,
        "status": "started",
        "request": packet,
        "decision": None,
        "error": None,
    }
    store.put("decision", key, record)
    try:
        isolated = Request(**{**clone(packet), "actions": tuple(clone(packet["actions"]))})
        decision = _validate_decision(policy.decide(isolated), request)
    except Exception as exc:
        record.update(
            status="failed",
            error={
                "type": type(exc).__name__,
                "message": str(exc)
                if isinstance(exc, PolicyError)
                else "Participant execution failed",
                "receipt": exc.receipt if isinstance(exc, PolicyError) else {},
            },
        )
        store.put("decision", key, record)
        raise RunBlocked(f"Decision {key} failed; inspect the record before retrying") from exc
    record.update(status="completed", decision=decision)
    store.put("decision", key, record)
    return decision


def _episode(
    store: RunStore,
    key: str,
    world: World,
    policies: dict[str, Policy],
    agents: list[AgentConfig],
    seed: int,
    repetition: int,
    condition: str,
    experiment: Experiment,
    retry_failed: bool,
) -> None:
    episode = store.get("episode", key)
    if episode is None:
        episode = {
            "condition": condition,
            "seed": seed,
            "repetition": repetition,
            "status": "running",
            "step": 0,
            "state": clone(world.initial(tuple(a.id for a in agents), seed)),
            "memories": {a.id: {} for a in agents},
            "outcomes": None,
        }
        store.put("episode", key, episode)
    if episode["status"] == "completed":
        return
    while not world.finished(clone(episode["state"])):
        step = episode["step"]
        if step >= experiment.limits.max_steps:
            raise RunBlocked(f"Episode {key} reached the {experiment.limits.max_steps} step limit")
        state = episode["state"]
        active = world.active(clone(state))
        ids = {agent.id for agent in agents}
        if not active or len(set(active)) != len(active) or set(active) - ids:
            raise ConfigurationError("World must expose distinct, known active participants")
        # Freeze every view before asking any participant at this decision boundary.
        requests = []
        for actor in active:
            menu = tuple(clone(world.actions(clone(state), actor)))
            if not menu or any(not isinstance(action, dict) for action in menu):
                raise ConfigurationError("World action menus must contain JSON objects")
            if len({canonical(a) for a in menu}) != len(menu):
                raise ConfigurationError("World action menus must not contain duplicates")
            instructions = next(a.instructions for a in agents if a.id == actor)
            requests.append(
                Request(
                    actor,
                    step,
                    _request_seed(seed, repetition, step, actor),
                    clone(world.observe(clone(state), actor)),
                    menu,
                    clone(episode["memories"][actor]),
                    instructions,
                )
            )
        decisions = {
            request.actor: _choose(
                store,
                key,
                request,
                policies[request.actor],
                retry_failed=retry_failed,
                limit=experiment.limits.max_decisions,
            )
            for request in requests
        }
        new_state = clone(
            world.advance(clone(state), {a: clone(d["action"]) for a, d in decisions.items()})
        )
        if not isinstance(new_state, dict):
            raise ConfigurationError("World.advance must return a JSON object")
        episode["state"] = new_state
        episode["step"] += 1
        for actor, decision in decisions.items():
            episode["memories"][actor] = decision["memory"]
        store.put("episode", key, episode)
    episode.update(status="completed", outcomes=clone(world.outcomes(clone(episode["state"]))))
    store.put("episode", key, episode)


def run(
    experiment: Experiment,
    output: str | Path,
    *,
    registry: Registry | None = None,
    retry_failed: bool = False,
) -> RunResult:
    """Create or resume a run. Configurations and implementation identities must match.

    A failed or interrupted decision requires explicit retry consent because an
    external call may have completed remotely without a locally stored response.
    """
    # Isolate the execution design from caller-owned nested dictionaries and lists.
    experiment = Experiment.model_validate(experiment.model_dump(mode="json"))
    registry = registry or default_registry()
    spec = specification(experiment, registry)
    fingerprint = digest(spec)
    for condition in experiment.conditions:
        for policy in _policies(experiment, condition, registry).values():
            if isinstance(policy, ModelPolicy):
                policy.check_available()
    directory = Path(output).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    try:
        with (
            FileLock(directory / ".run.lock", timeout=0),
            RunStore(directory / "run.sqlite") as store,
        ):
            store.verify()
            manifest = store.get("manifest", "run")
            if manifest and manifest["fingerprint"] != fingerprint:
                raise IntegrityError(
                    "Configuration, Python version or implementation changed; "
                    "use a new output directory"
                )
            if manifest is None:
                if store.events():
                    raise IntegrityError("Existing journal has no run manifest")
                manifest = {"fingerprint": fingerprint, "specification": spec}
                store.put("manifest", "run", manifest)
            write_json(directory / "manifest.json", manifest)
            index = 0
            for condition in experiment.conditions:
                for seed in experiment.seeds:
                    for repetition in range(experiment.repetitions):
                        index += 1
                        world = registry.world(
                            experiment.world.kind,
                            {**experiment.world.parameters, **condition.world},
                        )
                        _episode(
                            store,
                            f"e{index:06d}",
                            world,
                            _policies(experiment, condition, registry),
                            experiment.agents,
                            seed,
                            repetition,
                            condition.name,
                            experiment,
                            retry_failed,
                        )
            store.verify()
            return RunResult(
                directory,
                fingerprint,
                sum(e["status"] == "completed" for e in store.items("episode").values()),
                index,
                store.attempts(),
            )
    except Timeout as exc:
        raise RunBlocked("Another process is already writing this run") from exc
