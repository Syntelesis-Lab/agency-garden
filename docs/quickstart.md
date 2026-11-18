# Run your first experiment

## Install

Use Python 3.11 or newer in a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install 'agency-garden @ git+https://github.com/Syntelesis-Lab/agency-garden.git@v0.1.0a2'
agency-garden --version
```

On Windows, activate with `.venv\Scripts\activate`. Git is required for this installation command; GitHub authentication is not. You can alternatively install the wheel from the [a2 GitHub release](https://github.com/Syntelesis-Lab/agency-garden/releases/tag/v0.1.0a2), which does not require Git. PyPI publication remains disabled. No compiler, database service, Node.js installation or API key is required for the default examples.

## Create and run

```bash
agency-garden init commons my-study
agency-garden plan my-study/experiment.toml
agency-garden run my-study/experiment.toml --output my-study/run
agency-garden view my-study/run
```

The default Commons experiment has four participants, five rounds, three seeds and two conditions. A successful run completes six episodes and records 120 decision attempts. `plan` validates configuration and implementation identity without contacting a provider.

`view` opens a self-contained HTML report in your default browser. It needs no server or internet connection. If automatic opening is unavailable, open `my-study/run/report.html` yourself.

| Output | Purpose |
|---|---|
| `manifest.json` | Frozen configuration, versions and source identities |
| `run.sqlite` | Authoritative journal, decisions and world checkpoints |
| `report.json` | Machine-readable descriptive summary |
| `report.html` | Offline explorer with condition summaries and histories |

SQLite may create `-wal` and `-shm` sidecars while open. Close writers before copying a run directory; retain sidecars if copying an active database. The `.run.lock` file coordinates writers and can remain after completion.

## Change something

Edit `rounds`, the pool `multiplier`, a private-need range or a participant policy in `experiment.toml`. Use a new output directory:

```bash
agency-garden run my-study/experiment.toml --output my-study/changed-run
```

Using the same directory with changed configuration or implementation is rejected. Re-running the unchanged experiment resumes it and reuses completed decisions.

## Inspect the private record

```bash
agency-garden report my-study/run --include-private
```

This writes `report.private.json` and `report.private.html`, including observations, memory, reasons and provider receipts. Ordinary reports omit those fields. Actions and game-defined outcomes can still reveal information, so review exports before sharing.

Next: [configuration](configuration.md), [world mechanics](worlds.md), [model participants](models.md) and [extensions](extensions.md).
