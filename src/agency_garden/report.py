"""Portable summaries and a self-contained, offline evidence viewer."""

import json
from collections import Counter, defaultdict
from importlib.resources import files
from pathlib import Path
from statistics import mean
from typing import Any

from agency_garden.contracts import JSONObject
from agency_garden.errors import ConfigurationError
from agency_garden.serialization import write_json
from agency_garden.store import RunStore


def _numbers(value: Any, prefix: str = "") -> dict[str, float]:
    if isinstance(value, dict):
        result = {}
        for key, child in value.items():
            result.update(_numbers(child, f"{prefix}.{key}" if prefix else key))
        return result
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return {prefix: float(value)}
    return {}


def read_run(directory: str | Path, *, include_private: bool = False) -> JSONObject:
    """Read and verify one consistent database snapshot before preparing an export."""
    database = Path(directory) / "run.sqlite"
    if not database.is_file():
        raise ConfigurationError(f"No run database at {database}")
    with RunStore(database, read_only=True) as store:
        store.connection.execute("BEGIN")
        integrity = store.verify()
        manifest = store.get("manifest", "run")
        if not manifest:
            raise ConfigurationError("The database does not contain an experiment")
        episodes, decisions, events = (
            store.items("episode"),
            store.items("decision"),
            store.events(),
        )
    experiment = manifest["specification"]["experiment"]
    planned_per_condition = len(experiment["seeds"]) * experiment["repetitions"]
    groups = []
    for condition in experiment["conditions"]:
        records = [ep for ep in episodes.values() if ep["condition"] == condition["name"]]
        complete = [ep for ep in records if ep["status"] == "completed"]
        metrics: dict[str, list[float]] = defaultdict(list)
        for episode in complete:
            for key, number in _numbers(episode["outcomes"]).items():
                metrics[key].append(number)
        groups.append(
            {
                "name": condition["name"],
                "planned": planned_per_condition,
                "completed": len(complete),
                "incomplete": len(records) - len(complete),
                "not_started": planned_per_condition - len(records),
                "metrics": {
                    key: {
                        "mean": mean(values),
                        "n": len(values),
                        "min": min(values),
                        "max": max(values),
                    }
                    for key, values in sorted(metrics.items())
                },
            }
        )
    exported_episodes = []
    for key, episode in episodes.items():
        exported = {
            "id": key,
            **{
                k: v
                for k, v in episode.items()
                if include_private or k not in {"state", "memories"}
            },
        }
        exported_episodes.append(exported)
    exported_decisions = []
    for key, decision in decisions.items():
        if include_private:
            exported_decisions.append({"id": key, **decision})
        else:
            exported_decisions.append(
                {
                    "id": key,
                    "episode": decision["episode"],
                    "actor": decision["actor"],
                    "step": decision["step"],
                    "attempt": decision["attempt"],
                    "status": decision["status"],
                    "action": decision["decision"]["action"] if decision["decision"] else None,
                    "error_type": decision["error"]["type"] if decision["error"] else None,
                }
            )
    attempts = 0
    usage: Counter[str] = Counter()
    for event in events:
        payload = event["payload"]
        if payload["kind"] != "decision":
            continue
        value = payload["value"]
        attempts += int(value["status"] == "started")
        receipt = (
            (value.get("decision") or {}).get("receipt")
            or (value.get("error") or {}).get("receipt")
            or {}
        )
        reported = receipt.get("usage") or (receipt.get("receipt") or {}).get("usage") or {}
        for key, number in reported.items():
            if isinstance(number, int) and not isinstance(number, bool):
                usage[key] += number
    return {
        "schema_version": 1,
        "name": experiment["name"],
        "description": experiment["description"],
        "fingerprint": manifest["fingerprint"],
        "engine_version": manifest["specification"]["engine_version"],
        "includes_private": include_private,
        "integrity": integrity,
        "planned": planned_per_condition * len(groups),
        "completed": sum(group["completed"] for group in groups),
        "attempts": attempts,
        "reported_usage": dict(usage),
        "conditions": groups,
        "episodes": exported_episodes,
        "decisions": exported_decisions,
        "interpretation": "Descriptive game outcomes, not moral or welfare scores. "
        "Episodes sharing a configuration are not automatically independent. "
        "Reported token usage may be incomplete for failed or uncertain calls.",
    }


def write_report(directory: str | Path, *, include_private: bool = False) -> tuple[Path, Path]:
    data = read_run(directory, include_private=include_private)
    root = Path(directory)
    suffix = ".private" if include_private else ""
    json_path = root / f"report{suffix}.json"
    html_path = root / f"report{suffix}.html"
    write_json(json_path, data)
    # JSON is embedded as data, never interpolated into executable JavaScript or HTML.
    encoded = json.dumps(data, ensure_ascii=True, allow_nan=False).replace("<", "\\u003c")
    template = files("agency_garden").joinpath("templates/report.html").read_text(encoding="utf-8")
    html_path.write_text(template.replace("__GARDEN_DATA__", encoded), encoding="utf-8")
    return json_path, html_path
