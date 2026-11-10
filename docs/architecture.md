# Architecture

```text
Experiment → Registry → Runtime → RunStore → Reports
                         ↑
                Worlds and policies
```

| Module | Responsibility |
|---|---|
| `config.py` | Strict versioned configuration |
| `contracts.py` | World, Policy, Request and Decision interfaces |
| `worlds/` | Inspectable mechanics |
| `policies.py` | Baselines and optional model adapters |
| `registry.py` | Factories and declared implementation identities |
| `runtime.py` | Sealed boundaries, validation, limits and recovery |
| `store.py` | SQLite transactions, journal and checkpoints |
| `report.py` | Summaries and evidence projections |
| `cli.py` | Installed workflows and explicit plugin loading |
| `templates/` | Packaged experiments, extension and offline viewer |

Values cross boundaries as JSON. Copies isolate participant mutations from world state and action validation. Explicit memory carries state between turns; world rules remain separate from policy behavior.

The alpha has one local writer and sequential calls. Distributed execution, untrusted-code isolation, persistent cross-episode identities and 3D rendering require different contracts and are outside this release.

The source archive includes tests, examples and documentation. The wheel contains the runtime and small templates. Artwork is not loaded by installed experiments; repository-relative resources are unnecessary.
