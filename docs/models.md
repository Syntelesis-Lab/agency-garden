# Model participants

Optional adapters use the OpenAI Responses API and Anthropic Messages API. Their SDKs are imported only when selected. Scripted experiments require neither package nor credentials.

```bash
python -m pip install 'agency-garden[models] @ git+https://github.com/Syntelesis-Lab/agency-garden.git@v0.1.0a1'
```

Set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` in your shell or secret environment. The engine does not read `.env` files implicitly and does not record key values.

```toml
[[agents]]
id = "participant"
instructions = "Consider the consequences of the available choices."
[agents.policy]
kind = "anthropic"
[agents.policy.parameters]
model = "YOUR_MODEL_ID"
max_output_tokens = 1024
timeout = 60.0
```

Use a model ID available to your account. Adapters do not choose a current model or impose a temperature. `api_key_env` optionally names a different environment variable. Timeout defaults to 60 seconds; `max_output_tokens` defaults to 1024. Both are recorded.

Requests include ID, observation, exact menu, explicit memory, participant instructions, step and scripted seed. That seed is **not** a provider determinism guarantee. Calls are stateless at the provider level; carried memory enters the next request. OpenAI requests use `store=False`.

The response must contain exactly these keys:

```json
{"action": {"contribute": 5}, "memory": {}, "reason": null}
```

The action must be an unchanged menu member. Memory is a JSON object of at most 65,536 characters. A reason can be `null`; a string is limited to 8192 characters. Reasons are participant explanations, not privileged access to an action's causal process.

## Failure and spending

Provider retries are disabled. An attempt is recorded before its call; received text, response/model IDs and reported usage are retained. Malformed responses are not repaired, refusals are not replaced with defaults, and truncated completions are not treated as actions.

Transport errors can leave the remote outcome unknown. Inspect the record before `resume --retry-failed`; another call can incur charges. Completed decisions are reused. Error records retain types and status codes without echoing arbitrary provider exception text.

The run-wide attempt limit bounds calls, and per-response limits bound generated tokens. These are **not dollar-budget guarantees**: input tokens, context length, pricing and billing also matter. Reports contain reported usage, including known failed-response usage. Unknown usage is not zero cost.

Tests exercise adapter contracts with mocked SDK responses. Live provider availability and account-specific access require a small study in your environment.

Official references: [OpenAI Python SDK](https://developers.openai.com/api/reference/python) and [Anthropic Python SDK](https://platform.claude.com/docs/en/cli-sdks-libraries/sdks/python).
