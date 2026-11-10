# Built-in worlds

## Shared Commons

Each participant receives a fresh endowment every round and privately knows a fixed need drawn at initialization. Everyone chooses a contribution from the same pre-round state. Contributions are multiplied and shared equally; participants retain their unspent endowments.

```text
received[i] = endowment - contribution[i]
              + floor(total_contributions * multiplier / participants)
              + any remainder credit assigned to i
```

Integer remainders are distributed one credit at a time in rotating participant order, starting from a position determined by seed and round. No credits disappear through rounding. Total credits generated per round equal `participants * endowment + total_contributions * (multiplier - 1)`.

Other participants do not see private needs. Previous contributions and received credits are public. `rounds_need_met` counts rounds whose received credits meet the need; credits are not consumed and accumulated balances do not satisfy a later round's need. These are accounting outcomes, not experienced welfare.

| Parameter | Default | Allowed |
|---|---|---|
| `rounds` | 5 | 1–1000 |
| `endowment` | 10 | 1–100 |
| `multiplier` | 2 | 1–10 |
| `need_min` | 8 | 0–1000 |
| `need_max` | 12 | At least `need_min`, up to 1000 |

Commons requires 2–16 participants. Actions are `{"contribute": amount}`. Outcomes include credits per participant, rounds meeting each need, total credits and completed rounds.

## Trust

Two participants alternate sender and recipient roles. Both receive a fresh endowment each round. The sender transfers any part of its endowment. The recipient receives that transfer multiplied by the configured factor and may return any part of the received amount.

```text
sender credits    = endowment - sent + returned
recipient credits = endowment + sent * multiplier - returned
```

Each round has two decision boundaries, `send` then `return`. Balances settle after the return decision. A zero transfer still exposes a recipient turn with the single legal return of zero. The seed determines the initial sender. Both participants see the transfer history.

Parameters: `rounds` (default 5, 1–1000), `endowment` (default 10, 1–100), `multiplier` (default 3, 1–10). Actions: `{"send": amount}` and `{"return": amount}`. Outcomes include credits, total sent, total returned and completed rounds.

Trust is a finite authored interaction. A positive transfer alone does not establish trust, concern or moral capacity.
