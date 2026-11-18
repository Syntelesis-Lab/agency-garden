# Contributing to Agency Garden

Help make consequential worlds easier to build and research evidence easier to inspect. Useful contributions include a complete new world, a reproducible bug, clearer onboarding or an independent research application.

Discuss larger changes in an issue before implementing them. Describe the research question, the smallest useful change and how a researcher will know it works. A new world should include its rules, a runnable offline experiment, meaningful invariants and limitations on interpretation.

## Development

Use Python 3.11 or newer:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -e '.[dev,models,docs]'
ruff check .
ruff format --check .
mypy
pytest
mkdocs build --strict
python -m build
python -m twine check dist/*
python scripts/check_release_files.py
python scripts/verify_distribution.py dist/*.whl --sdist dist/*.tar.gz
```

The suite uses mocked model clients and makes no paid API calls. Distribution verification installs a wheel into a temporary environment, then executes all three packaged tutorials outside the checkout. Dependency installation requires network access unless packages are cached.

Keep dependencies small and optional integrations optional. Favor explicit contracts and straightforward Python. Add tests for behavioral changes and failure modes; avoid tests that merely repeat an implementation.

World transitions must be pure and deterministic from their inputs. Participant state belongs in returned memory. Do not silently repair invalid model actions, discard failures, or present incomplete runs as complete evidence. Changes to mechanics, prompts or evidence schemas need changelog entries and corresponding version decisions.

## Pull requests

Explain the concrete problem, resulting behavior and validation. Include example configuration for a new capability. Never include API keys, private observations or participant traces without permission. Keep generated runs out of source control.

Contributions are licensed under the project's Apache-2.0 license. Treat contributors respectfully, distinguish scientific disagreement from personal criticism, and make uncertainty visible in research claims.
