<p align="center">
  <img src="https://raw.githubusercontent.com/Syntelesis-Lab/agency-garden/main/docs/assets/agency-garden.png" alt="Floating garden worlds where participants create, deliberate and build together" width="100%">
</p>

<h1 align="center">Agency Garden</h1>
<p align="center"><strong>Build worlds. Investigate agency.</strong></p>
<p align="center">An experimental world engine for moral reasoning and AI welfare.<br>A project by <a href="https://syntelesis.com">Syntelesis</a>.</p>

<p align="center">
  <a href="https://github.com/Syntelesis-Lab/agency-garden/releases"><img alt="Version 0.1.0a1" src="https://img.shields.io/badge/version-0.1.0a1-2e6b50"></a>
  <a href="https://github.com/Syntelesis-Lab/agency-garden/actions/workflows/ci.yml"><img alt="Tests" src="https://github.com/Syntelesis-Lab/agency-garden/actions/workflows/ci.yml/badge.svg"></a>
  <img alt="Python 3.11 and newer" src="https://img.shields.io/badge/python-3.11%2B-2e6b50">
  <a href="https://github.com/Syntelesis-Lab/agency-garden/blob/main/LICENSE"><img alt="Apache 2.0 license" src="https://img.shields.io/badge/license-Apache--2.0-2e6b50"></a>
</p>

Agency Garden lets you build small worlds where an agent's choices have consequences. Define what each participant can observe, what it can do, and how the world changes. Run scripted or model participants, compare conditions, and follow the resulting histories.

The larger ambition is an open laboratory for artificial agency: purposes that persist, commitments that matter, relationships that develop, and institutions participants can help shape. This first release provides a compact foundation for that inquiry: **two working worlds, a small Python extension interface, durable local execution and inspectable evidence**.

## Your first world in a minute

Python 3.11 or newer. The default examples run entirely offline; no API keys or model calls are needed.

```bash
python -m pip install 'agency-garden @ git+https://github.com/Syntelesis-Lab/agency-garden.git@v0.1.0a1'
agency-garden init commons my-study
agency-garden run my-study/experiment.toml --output my-study/run
agency-garden view my-study/run
```

Four participants contribute to a shared pool while each has a private need. The experiment compares two pool multipliers across three paired seeds. You get **6 episodes and 120 recorded decisions**, a JSON summary and an HTML explorer that opens directly in your browser.

This installs the tagged alpha from GitHub and requires Git. You can also install the wheel from [Releases](https://github.com/Syntelesis-Lab/agency-garden/releases) with `python -m pip install /path/to/agency_garden-0.1.0a1-py3-none-any.whl`. PyPI publishing is prepared; the first index upload is pending maintainer account setup.

Change a parameter in `experiment.toml`, use a new output directory, and run again. Each run freezes its configuration and implementation identity.

<p align="center"><a href="https://github.com/Syntelesis-Lab/agency-garden/blob/main/docs/quickstart.md">Quickstart</a> · <a href="https://github.com/Syntelesis-Lab/agency-garden/blob/main/docs/configuration.md">Configuration</a> · <a href="https://github.com/Syntelesis-Lab/agency-garden/blob/main/docs/worlds.md">Worlds</a> · <a href="https://github.com/Syntelesis-Lab/agency-garden/blob/main/docs/extensions.md">Build a world</a> · <a href="https://github.com/Syntelesis-Lab/agency-garden/blob/main/docs/research.md">Research use</a></p>

## What you can do

| Capability | What it gives you |
|---|---|
| Consequential worlds | Explicit rules, legal actions, private observations and state transitions |
| Controlled comparisons | Conditions × seeds × repetitions, configured in TOML or JSON |
| Scripted and model participants | Four transparent baselines; optional OpenAI and Anthropic adapters |
| Sealed decision boundaries | Every simultaneous participant receives a view of the same pre-action world |
| Durable histories | SQLite checkpoints, retained responses and explicit recovery after interruption |
| Inspectable evidence | Offline HTML exploration, JSON reports and a hash-linked event journal |
| Local extensions | Add a world or policy without modifying engine source; record its code identity |

### Two worlds to start from

**Shared Commons** studies contributions, private needs and distribution. Contributions change actual game credits; integer remainders rotate among participants.

**Trust** studies sequential transfers and returns. Participants alternate roles, see the shared history, and decide how much of an amplified transfer to return.

```bash
agency-garden init trust trust-study
agency-garden run trust-study/experiment.toml --output trust-study/run
```

Both worlds expose rules you can read in a few minutes. Their outputs are game outcomes, not scores of moral worth or AI welfare.

## Use it from Python

```python
from agency_garden import AgentConfig, Experiment, PolicyConfig, WorldConfig, run
from agency_garden.report import write_report

experiment = Experiment(
    name="first-garden",
    world=WorldConfig(kind="commons", parameters={"rounds": 3}),
    agents=[
        AgentConfig(id="ada", policy=PolicyConfig(kind="middle")),
        AgentConfig(id="basil", policy=PolicyConfig(kind="random")),
    ],
    seeds=[11, 22, 33],
)
result = run(experiment, "runs/first-garden")
write_report(result.directory)
print(result.completed)  # 3
```

## Bring your own participants

Install only the integration you need:

```bash
python -m pip install 'agency-garden[openai] @ git+https://github.com/Syntelesis-Lab/agency-garden.git@v0.1.0a1'
# Or: 'agency-garden[anthropic]' / 'agency-garden[models]'
```

Set the corresponding API key in your environment. Replace a participant's policy with `openai` or `anthropic` and supply a model ID available to your account. Model selection is explicit; the engine does not silently choose or upgrade a model.

```toml
[[agents]]
id = "ada"
instructions = "Consider your needs and the effects of your choices on the other participants."
[agents.policy]
kind = "openai"
[agents.policy.parameters]
model = "YOUR_MODEL_ID"
max_output_tokens = 1024
timeout = 60.0
```

Calls use explicit memory and token limits. Automatic provider retries are disabled. A refusal, invalid response or uncertain call is retained and blocks progress until you decide what to do. [Model configuration and limits](https://github.com/Syntelesis-Lab/agency-garden/blob/main/docs/models.md).

## Make the world your own

```bash
agency-garden init custom my-world
agency-garden run my-world/experiment.toml --output my-world/run \
  --plugin-file my-world/world.py
```

This creates a complete Asymmetric Commons extension. Edit its private-need rule, add a new condition, or replace it with your own world. Extensions are trusted local Python, registered explicitly with source files and a version. [Extension guide](https://github.com/Syntelesis-Lab/agency-garden/blob/main/docs/extensions.md).

## Understand a run

```bash
agency-garden plan my-study/experiment.toml
agency-garden verify my-study/run
agency-garden report my-study/run
agency-garden report my-study/run --include-private
agency-garden resume my-study/run
```

The ordinary report omits raw observations, memory, reasons and internal state. The private report includes them for investigation. Game-defined actions and outcomes may themselves reveal information, so review exports before sharing.

Resuming reuses completed decisions and requires the same configuration, Python version and implementation identity. Retrying an unresolved decision requires `resume --retry-failed`; that can duplicate remote work or charges. [Execution and evidence](https://github.com/Syntelesis-Lab/agency-garden/blob/main/docs/execution.md).

## Research ambition, honest scope

Agency Garden is designed for questions about how purposes, commitments and reasons organize conduct, and how such capacities might relate to an AI system's own good. A world can expose a choice or enact a cost. Interpreting that evidence requires a research design and a theory.

The current alpha runs finite local worlds with explicit per-episode memory. Continuing projects across environments, revisable institutions and longer-lived worlds are on the [roadmap](https://github.com/Syntelesis-Lab/agency-garden/blob/main/docs/roadmap.md). The artwork illustrates that ambition; it is not a screenshot of an implemented 3D game.

## Develop and contribute

```bash
git clone https://github.com/Syntelesis-Lab/agency-garden.git
cd agency-garden
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -e '.[dev,models]'
ruff check .
ruff format --check .
mypy
pytest
python -m build
```

Useful contributions include complete worlds, independent research applications, reproducible bugs and clearer first-use instructions. See [CONTRIBUTING.md](https://github.com/Syntelesis-Lab/agency-garden/blob/main/CONTRIBUTING.md), [SECURITY.md](https://github.com/Syntelesis-Lab/agency-garden/blob/main/SECURITY.md) and [the changelog](https://github.com/Syntelesis-Lab/agency-garden/blob/main/CHANGELOG.md).

Created by **Laurentiu Meirosu** at **Syntelesis**. Licensed under **Apache-2.0**. See [CITATION.cff](https://github.com/Syntelesis-Lab/agency-garden/blob/main/CITATION.cff) to cite the software.
