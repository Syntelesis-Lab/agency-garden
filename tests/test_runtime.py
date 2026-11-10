import sqlite3
from contextlib import closing

import pytest
from filelock import FileLock

from agency_garden import Decision, Limits, default_registry, run
from agency_garden.errors import ConfigurationError, IntegrityError, RunBlocked
from agency_garden.report import read_run
from agency_garden.store import RunStore


def registry_with(policy, source=__file__):
    registry = default_registry()
    registry.register_policy("probe", lambda **kwargs: policy, version="1", files=[source])
    return registry


def with_probe(experiment):
    data = experiment.model_dump()
    for agent in data["agents"]:
        agent["policy"] = {"kind": "probe"}
    return type(experiment).model_validate(data)


def test_completed_run_is_reused_without_new_attempts(experiment, tmp_path):
    result = run(experiment, tmp_path)
    assert (result.completed, result.episodes, result.attempts) == (2, 2, 8)
    assert run(experiment, tmp_path).attempts == 8
    report = read_run(tmp_path)
    assert report["integrity"]["valid"]
    assert report["conditions"][0]["completed"] == 2


def test_changed_configuration_cannot_resume(experiment, tmp_path):
    run(experiment, tmp_path)
    changed = experiment.model_copy(update={"name": "different"})
    with pytest.raises(IntegrityError, match="changed"):
        run(changed, tmp_path)


def test_interruption_retains_completed_decisions(experiment, tmp_path):
    class Interrupted:
        count = 0

        def decide(self, request):
            self.count += 1
            if self.count == 2:
                raise KeyboardInterrupt
            return Decision(request.actions[0])

    policy = Interrupted()
    registry = registry_with(policy)
    config = with_probe(experiment)
    with pytest.raises(KeyboardInterrupt):
        run(config, tmp_path, registry=registry)
    assert policy.count == 2
    with pytest.raises(RunBlocked, match="started"):
        run(config, tmp_path, registry=registry)
    assert policy.count == 2
    result = run(config, tmp_path, registry=registry, retry_failed=True)
    assert result.attempts == 9
    assert policy.count == 9
    with RunStore(tmp_path / "run.sqlite", read_only=True) as store:
        assert store.verify()["valid"]
        assert next(iter(store.items("decision").values()))["attempt"] == 1


def test_failed_decision_is_never_replaced_with_a_default(experiment, tmp_path):
    class Invalid:
        def decide(self, request):
            return Decision({"not-an-action": 99})

    config = with_probe(experiment)
    with pytest.raises(RunBlocked):
        run(config, tmp_path, registry=registry_with(Invalid()))
    report = read_run(tmp_path)
    assert report["completed"] == 0
    assert report["conditions"][0]["not_started"] == 1
    assert report["conditions"][0]["metrics"] == {}
    assert report["decisions"][0]["status"] == "failed"
    assert report["decisions"][0]["action"] is None


def test_mutating_the_request_cannot_expand_the_action_menu(experiment, tmp_path):
    class Mutating:
        def decide(self, request):
            request.actions[0]["contribute"] = 999
            return Decision(request.actions[0])

    with pytest.raises(RunBlocked):
        run(with_probe(experiment), tmp_path, registry=registry_with(Mutating()))


def test_boolean_action_is_not_integer_action(experiment, tmp_path):
    class Boolean:
        def decide(self, request):
            return Decision({"contribute": True})

    with pytest.raises(RunBlocked):
        run(with_probe(experiment), tmp_path, registry=registry_with(Boolean()))


def test_memory_and_observations_are_sealed(experiment, tmp_path):
    seen = []

    class Remembering:
        def decide(self, request):
            seen.append(
                (
                    request.actor,
                    request.step,
                    request.memory.copy(),
                    len(request.observation["history"]),
                )
            )
            request.observation["history"].append({"fake": True})
            return Decision(
                request.actions[0], memory={"turns": request.memory.get("turns", 0) + 1}
            )

    run(with_probe(experiment), tmp_path, registry=registry_with(Remembering()))
    assert seen[:4] == [
        ("ada", 0, {}, 0),
        ("basil", 0, {}, 0),
        ("ada", 1, {"turns": 1}, 1),
        ("basil", 1, {"turns": 1}, 1),
    ]
    assert seen[4][2] == {}


@pytest.mark.parametrize("limit", [1, 3])
def test_decision_limit_includes_started_attempts(experiment, tmp_path, limit):
    config = experiment.model_copy(update={"limits": Limits(max_decisions=limit)})
    with pytest.raises(RunBlocked, match="limit"):
        run(config, tmp_path)
    assert read_run(tmp_path)["attempts"] == limit


def test_step_limit(experiment, tmp_path):
    config = experiment.model_copy(update={"limits": Limits(max_steps=1)})
    with pytest.raises(RunBlocked, match="step limit"):
        run(config, tmp_path)


def test_a_second_writer_is_rejected(experiment, tmp_path):
    with FileLock(tmp_path / ".run.lock"), pytest.raises(RunBlocked, match="Another process"):
        run(experiment, tmp_path)


@pytest.mark.parametrize("table", ["objects", "events"])
def test_tampering_is_detected(experiment, tmp_path, table):
    run(experiment, tmp_path)
    with closing(sqlite3.connect(tmp_path / "run.sqlite")) as connection, connection:
        if table == "objects":
            connection.execute("UPDATE objects SET body='{}' WHERE kind='episode'")
        else:
            connection.execute("UPDATE events SET payload='{}' WHERE seq=2")
    with pytest.raises(IntegrityError):
        read_run(tmp_path)


def test_plugin_source_change_invalidates_resume(experiment, tmp_path):
    source = tmp_path / "policy.py"
    source.write_text("# version one\n")

    class First:
        def decide(self, request):
            return Decision(request.actions[0])

    registry = registry_with(First(), source)
    config = with_probe(experiment)
    run(config, tmp_path / "run", registry=registry)
    source.write_text("# version two\n")
    with pytest.raises(IntegrityError, match="changed"):
        run(config, tmp_path / "run", registry=registry)


def test_duplicate_extension_rejected():
    registry = default_registry()
    with pytest.raises(ConfigurationError, match="already registered"):
        registry.register_policy("first", lambda: None, version="1", files=[__file__])
