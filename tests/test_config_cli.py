import json

import pytest

from agency_garden import Experiment
from agency_garden.cli import main
from agency_garden.config import load_experiment
from agency_garden.report import read_run, write_report


@pytest.mark.parametrize(
    "world,episodes,attempts", [("commons", 6, 120), ("trust", 6, 60), ("custom", 6, 60)]
)
def test_packaged_templates_end_to_end(tmp_path, world, episodes, attempts):
    directory = tmp_path / "study"
    assert main(["init", world, str(directory)]) == 0
    plugin = ["--plugin-file", str(directory / "world.py")] if world == "custom" else []
    assert main(["plan", str(directory / "experiment.toml"), *plugin]) == 0
    assert (
        main(
            ["run", str(directory / "experiment.toml"), "--output", str(directory / "run"), *plugin]
        )
        == 0
    )
    result = read_run(directory / "run")
    assert result["completed"] == episodes
    assert result["attempts"] == attempts
    assert main(["resume", str(directory / "run"), *plugin]) == 0
    assert main(["verify", str(directory / "run")]) == 0
    assert main(["report", str(directory / "run"), "--include-private"]) == 0
    assert (directory / "run/report.html").is_file()
    assert (directory / "run/report.private.html").is_file()
    assert main(["init", world, str(directory)]) == 2


@pytest.mark.parametrize(
    "change",
    [
        {"schema_version": 2},
        {"schema_version": True},
        {"seeds": [1, 1]},
        {"agents": [{"id": "a"}, {"id": "a"}]},
        {"seeds": [True]},
        {"conditions": [{"name": "x"}, {"name": "x"}]},
        {"conditions": [{"name": "x", "policies": {"absent": {"kind": "first"}}}]},
        {"secret_typo": 1},
    ],
)
def test_invalid_designs_fail(experiment, change):
    with pytest.raises(ValueError):
        Experiment.model_validate({**experiment.model_dump(), **change})


def test_json_matches_toml(tmp_path):
    main(["init", "commons", str(tmp_path / "study")])
    original = load_experiment(tmp_path / "study/experiment.toml")
    path = tmp_path / "same.json"
    path.write_text(original.model_dump_json())
    assert load_experiment(path) == original


def test_public_report_omits_raw_private_data(experiment, tmp_path):
    from agency_garden import run

    run(experiment, tmp_path)
    public = read_run(tmp_path)
    private = read_run(tmp_path, include_private=True)
    assert "state" not in public["episodes"][0]
    assert "request" not in public["decisions"][0]
    assert "your_need" in private["decisions"][0]["request"]["observation"]


def test_html_escapes_script_injection(experiment, tmp_path):
    from agency_garden import run

    dangerous = '</script><script>alert("unsafe")</script>'
    experiment = experiment.model_copy(update={"description": dangerous})
    run(experiment, tmp_path)
    _, html = write_report(tmp_path)
    text = html.read_text()
    assert dangerous not in text
    assert "\\u003c/script>" in text
    assert json.loads((tmp_path / "report.json").read_text())["description"] == dangerous


def test_schema_and_list(tmp_path, capsys):
    assert main(["schema", "--output", str(tmp_path / "schema.json")]) == 0
    assert json.loads((tmp_path / "schema.json").read_text())["properties"]["schema_version"]
    assert main(["list"]) == 0
    assert "commons" in capsys.readouterr().out


def test_missing_config_is_actionable(tmp_path, capsys):
    assert main(["run", str(tmp_path / "missing.toml"), "--output", str(tmp_path / "out")]) == 2
    assert "Cannot load" in capsys.readouterr().err
