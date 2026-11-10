# Configure an experiment

An experiment expands **conditions × seeds × repetitions** into episodes. Each episode starts a fresh world and explicit participant memories. Conditions share seeds and scripted random-choice seed derivation, allowing paired comparisons when the design supports them.

TOML and JSON are supported. Unknown fields, duplicate IDs, unsupported schema versions and malformed values fail before execution. Booleans are not integers. Generate the machine-readable schema with `agency-garden schema --output schema.json`.

```toml
schema_version = 1
name = "pool-returns"
description = "A comparison of two pool multipliers."
seeds = [11, 22, 33]
repetitions = 1

[world]
kind = "commons"
[world.parameters]
rounds = 5
multiplier = 2

[[agents]]
id = "ada"
[agents.policy]
kind = "middle"

[[agents]]
id = "basil"
[agents.policy]
kind = "random"

[[conditions]]
name = "baseline"

[[conditions]]
name = "higher-return"
[conditions.world]
multiplier = 3

[limits]
max_steps = 100
max_decisions = 1000
```

| Field | Meaning | Default |
|---|---|---|
| `schema_version` | Configuration schema, currently 1 | 1 |
| `name` | Human-readable identifier | Required |
| `world.kind` | Registered world | `commons` |
| `world.parameters` | World-specific settings | World defaults |
| `agents` | Unique IDs, policies and optional instructions | Required |
| `seeds` | Unique integer world seeds | `[1]` |
| `repetitions` | Separate repetitions of each seed/condition | 1 |
| `conditions` | Named interventions | One `baseline` |
| `limits.max_steps` | World transitions per episode | 1000 |
| `limits.max_decisions` | Participant attempts across the whole run | 10000 |

IDs start with an ASCII letter and contain letters, digits, hyphens or underscores, up to 64 characters. One experiment may expand to at most 100,000 episodes.

## Conditions

`conditions.world` shallowly replaces individual base-world parameters. To change a participant's policy, supply the complete replacement:

```toml
[[conditions]]
name = "different-participant"
[conditions.policies.ada]
kind = "last"
```

Only existing participant IDs may be overridden. Instructions remain those declared on the participant. Nested policy parameters are not implicitly merged.

## Scripted policies

`first`, `middle` and `last` select the corresponding action-menu position. `middle` selects index `len(actions) // 2`. `random` samples uniformly using a deterministic per-decision seed. These policies take no parameters and have no hidden moral objective.

Menu order belongs to the world: Commons lists contributions from zero upward; Trust lists transfers/returns from zero upward. When an intervention changes menu length, the same seeded random draw need not yield the same action. Repetitions vary the scripted random stream while preserving the configured initial-world seed.

## Limits and secrets

Attempts count even if they fail or are interrupted. A limit stops execution without inventing later outcomes. Limits are frozen configuration; changing one requires a new run.

Keys belong in environment variables. Configurations, instructions and custom plugin parameters are recorded as evidence, so do not put secrets in them.
