# Releases

Agency Garden uses Python package versions. The first candidate is `0.1.0a1`. A Git tag is `v` followed by the package version. Alpha status signals provisional APIs and a limited research foundation.

## Prepare a candidate

1. Update `src/agency_garden/_version.py`, `CHANGELOG.md` and `CITATION.cff` together.
2. Run the checks in `CONTRIBUTING.md`. CI tests supported Python versions and operating systems, builds documentation and verifies the installed distributions.
3. Inspect the source archive and wheel. Confirm no credentials, generated runs or private research records are included.
4. Push the commit and wait for CI to pass. Create the matching tag and a GitHub release describing changes and limitations.

Use the repository owner's Git identity for maintainer commits. Publishing does not create source commits.

## Configure PyPI once

A PyPI account owner must authorize a Trusted Publisher. For a new project, add a pending publisher in the account's Publishing settings:

| Field | Value |
|---|---|
| PyPI project | `agency-garden` |
| GitHub owner | `Syntelesis-Lab` |
| Repository | `agency-garden` |
| Workflow filename | `publish.yml` |
| Environment | `pypi` |

Create the `pypi` GitHub environment. An owner may add reviewers or tag restrictions appropriate to their release process. The workflow requests a short-lived PyPI credential through GitHub OIDC; no long-lived PyPI token belongs in this repository.

After configuring PyPI, run the **Publish to PyPI** workflow from GitHub Actions and supply the existing release tag. It runs the complete reusable validation workflow, checks that tag and package version match, builds distributions, and publishes the validated artifacts. If PyPI setup is incomplete, publication fails; a GitHub release alone does not make the package installable from PyPI.

The manual workflow also supports retrying a failed publication. PyPI versions cannot be overwritten. If a version already exists, inspect its files and provenance before changing anything; do not silently replace or skip files. After the first successful PyPI upload, switch installation examples to the index and update publication status in the documentation.

## Verify publication

Use a new virtual environment outside the checkout:

```bash
python -m pip install --pre 'agency-garden==0.1.0a1'
agency-garden --version
agency-garden init commons fresh-study
agency-garden run fresh-study/experiment.toml --output fresh-study/run
agency-garden verify fresh-study/run
```

Retain the published wheel and source archive with the tag. Research users should pin the version and record their complete environment because dependency and Python changes affect resume identity.

Official references: [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/) and [creating a pending publisher](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/).
