# Build a world or participant

Extensions are trusted Python. Start with a complete example:

```bash
agency-garden init custom my-world
agency-garden run my-world/experiment.toml --output my-world/run \
  --plugin-file my-world/world.py
```

The generated `world.py` subclasses Commons, changes the first participant's private need and registers `asymmetric`. Two conditions compare no added need with four added credits of need. Installed engine files remain untouched.

## World contract

| Method | Responsibility |
|---|---|
| `initial(actors, seed)` | Return initial JSON state |
| `active(state)` | Return distinct known active IDs |
| `observe(state, actor)` | Return that participant's JSON observation |
| `actions(state, actor)` | Return a nonempty tuple of distinct JSON action objects |
| `advance(state, actions)` | Apply collected actions; return next JSON state |
| `finished(state)` | Say whether the episode has ended |
| `outcomes(state)` | Return game-defined JSON outcomes |

Every observation and menu is constructed before simultaneous decisions are collected. Copies isolate world state; actions are validated against the original menu. A participant cannot expand its legal menu by mutating a request.

Transitions should be pure: deterministic from state/actions, with randomness derived from the initial seed and represented in state. Avoid external side effects in `advance`. A crash after decisions are recorded can cause an uncommitted transition to be recomputed.

## Policy contract

```python
from agency_garden import Decision, Request


class RememberingParticipant:
    def decide(self, request: Request) -> Decision:
        turns = request.memory.get("turns", 0)
        return Decision(
            action=request.actions[0],
            memory={"turns": turns + 1},
            reason=None,
        )
```

Persist state through `Decision.memory`, not instance fields: policies may be recreated during recovery. Memories reset per episode. The request seed supports deterministic scripted randomness without global random state.

## Register and identify

```python
from agency_garden import Registry


def register(registry: Registry) -> None:
    registry.register_policy(
        "remembering",
        RememberingParticipant,
        version="1",
        files=[__file__],
        dependencies=[],
    )
```

Declare all executable helper files affecting behavior and names of distribution dependencies. Source basenames must be distinct. Changing a declared file or dependency version prevents incompatible resume. Identity depends on complete declarations; it is not automatic discovery of every dependency or protection against hostile code.

In Python, call `default_registry()`, register extensions and pass `registry=registry` to `run`. `Registry()` starts empty. Duplicate names are rejected.

`--plugin-file` executes the selected file and calls `register(registry)`. Plugins have the user's permissions. Generated or untrusted executable code needs a separate isolation boundary outside this runtime.
