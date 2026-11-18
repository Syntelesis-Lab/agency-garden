# Publication readiness

The current source is an unreleased `0.1.0a2` candidate. The repository is private. Preparing it for public use does not authorize changing visibility, publishing a package, or deploying a website.

## What this alpha delivers

Agency Garden is an independent Python implementation with its own package, Git root, version history, documentation and release pipeline. Installation and examples need no other research checkout. Core runtime dependencies are PyPI packages; optional model integrations are separate extras. Standard GitHub Actions provide CI and packaging.

The supported boundary is deliberately small: two finite worlds, explicit participant memory, sealed decision boundaries, configurable comparisons, durable local execution and inspectable reports. Continuing histories, branching across worlds and richer institutions are future capabilities. They are not prerequisites for releasing this accurately described alpha, and they must not be advertised as implemented.

## Audit and repairs — 18 November 2026

The audit examined the runtime, storage, serialization, configuration, model adapters, world arithmetic, CLI, viewer, tests, package contents, licensing/provenance and GitHub configuration.

- All reachable original commits and their file contents were inspected for cross-project references and embedded local project paths. None were found. The original wheel and source archive were checked too. The repository is not a fork; its initial commit has no parent.
- The baseline suite passed 70 tests. New regression cases reproduce and reject ambiguous duplicate JSON keys in configurations and model responses. Rejected responses retain their original text and known usage.
- Dependency auditing found 13 advisory matches against the previously resolved filelock 3.32.7. The old upper bound prevented patched versions. The candidate requires filelock 4.2.1 or newer within major version 4; lock/recovery and clean-install checks are rerun against it. These package-level findings do not imply every affected lock class was used by this runtime.
- Generated next-step CLI commands now quote paths with spaces. The configuration documentation describes separately initialized episodes without asserting statistical independence.
- Publication now resolves an existing version tag to one explicitly approved commit. The same immutable commit is validated and packaged. Private repositories, disabled publication and unapproved commits cannot pass the preparation gate.
- A source-boundary check detects selected credential patterns and excluded runtime files. It does not prove that arbitrary secrets are absent. Review new contributions and archives before release.
- CI has an aggregate `release-check` and verifies Linux Python 3.11–3.14 plus macOS and Windows on Python 3.14. Distribution checks install the wheel and rebuild/install the source archive outside the checkout, without provider SDKs or paid model requests.

Existing a1 tags, releases and saved runs remain unchanged. A2 changes the engine identity; old runs need their original pinned code and environment.

## Repository settings

Preparation uses read-only workflow tokens, disallows Actions approving pull requests, requires full-SHA action pins, limits allowed Actions, enables dependency security updates and keeps publishing disabled. The `pypi` deployment environment is restricted to `main`.

The publication controls are intentionally separate:

| Control | Intended state before public release |
|---|---|
| Repository visibility | Private |
| PyPI workflow | Disabled |
| `PYPI_PUBLISH_ENABLED` | `false` |
| `PYPI_APPROVED_COMMIT` | `UNAPPROVED` |
| Main branch | Pull request plus successful `release-check`; no force-push or deletion |
| Provider keys / PyPI tokens | Not stored in the repository |
| Hosted documentation | Not deployed by this preparation |

GitHub rejected required environment reviewers for this private repository's current plan. The branch restriction and explicit workflow/commit gates remain available. Do not describe unavailable settings as enforced. After public-release approval, apply and verify the public-only settings listed below; no subscription upgrade is necessary merely to prepare the source.

## The later launch decision

Before changing visibility, confirm the exact candidate commit, green CI, dependency review, artifact hashes and accurate README. A public repository is useful without a PyPI release or a separately hosted website.

Immediately after an authorized visibility change, configure and verify:

- Approval for **all external contributors' fork workflows**.
- GitHub private vulnerability reporting, in addition to the existing private email route in `SECURITY.md`.
- Free public-repository secret scanning and push protection, as available for the account.
- A maintainer review requirement for the `pypi` environment, without administrator bypass.

These settings have different visibility/plan constraints. Recheck their actual API state at launch rather than treating this document as confirmation. See [GitHub Actions permissions](https://docs.github.com/en/rest/actions/permissions), [environment protection](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments), and [private vulnerability reporting](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository).

PyPI is a separate decision: an account owner must configure Trusted Publishing and approve the exact release commit. Follow [Releases](releasing.md). Keep the workflow disabled until then.

## Research and security limits

The tests establish software behavior within the exercised cases. They do not establish scientific validity of a new study, welfare, consciousness, or real-provider reliability. No paid model calls or independent human usability study formed part of this publication preparation. Custom Python is trusted code, not sandboxed code. Reports can disclose game-specific information even when raw private observations are omitted. Review exports deliberately.
