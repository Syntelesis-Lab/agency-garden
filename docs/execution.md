# Execution, recovery and evidence

## A decision boundary

1. Read a committed world checkpoint.
2. Construct all active participants' observations and menus.
3. Reuse completed decisions whose recorded requests match exactly.
4. Durably record each new attempt before invoking its policy.
5. Validate and record the decision, or retain a failure.
6. Apply valid actions and commit the next checkpoint.

Simultaneous rounds are sealed against same-round response leakage even though calls execute sequentially. Sequential worlds explicitly expose separate boundaries. Participant memory commits with the world state.

## Durability and identity

SQLite uses WAL and `synchronous=FULL`. An OS-backed lock permits one runtime writer. Each update writes a hash-linked event and materialized record in one transaction. Reporting reads a consistent snapshot.

The manifest records configuration, engine version, exact Python version, packaged Python source hashes, core dependency versions and declared extension identities. This is a strict resume contract, not a guarantee of reproducible model responses.

## Resume deliberately

```bash
agency-garden resume my-study/run
```

Completed decisions are reused. A provider may complete a call before a crash prevents its response being stored. That outcome is unknown locally, so the engine stops rather than silently repeating the call.

```bash
agency-garden report my-study/run --include-private
agency-garden resume my-study/run --retry-failed
```

The flag permits another attempt for failed/interrupted decisions. It can duplicate work or charges. Earlier attempts remain in the journal and count against the cap. Changing configuration, limits, code or dependencies requires a new run.

A failed custom transition leaves completed decisions intact. With unchanged code, resume recomputes it. Repairing the code changes its identity and requires a new run; preserve the failed record for diagnosis.

## Integrity and interpretation

```bash
agency-garden verify my-study/run
```

Verification checks sequence, chained hashes, manifest fingerprint and materialized records against the journal. It detects accidental modifications and inconsistent snapshots. It does not authenticate against a party replacing the whole database and all hashes.

Nor does it establish that rules model the intended situation, that participants understand it, or that a scientific interpretation follows. Those need separate examination.

```python
from agency_garden.store import RunStore

with RunStore("my-study/run/run.sqlite", read_only=True) as store:
    print(store.verify())
    events = store.events()
    decisions = store.items("decision")
```

The decision table contains the latest attempt per decision; the journal preserves earlier attempts and receipts. Reports summarize known usage across attempts while leaving uncertain usage unresolved.
