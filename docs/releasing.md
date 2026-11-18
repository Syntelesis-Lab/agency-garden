# Releases

Agency Garden uses Python package versions. Published versions are listed on [GitHub](https://github.com/Syntelesis-Lab/agency-garden/releases) and [PyPI](https://pypi.org/project/agency-garden/). A Git tag is `v` followed by the package version. Alpha status signals provisional APIs and a limited research foundation.

Version `0.1.0a3` corrects the product description and presentation to focus on moral reasoning. A new version preserves the immutable a2 distributions; published PyPI files and their embedded metadata cannot be replaced.

## Publication controls

Laurentiu Meirosu authorized the public repository and the `0.1.0a2` GitHub release on 18 November 2026. The audited tag and distribution hashes remain unchanged. The owner subsequently configured Trusted Publishing and authorized the PyPI upload of the same version. The workflow is disabled again after the verified publication; future uploads require a new explicit release approval. The `pypi` environment requires maintainer review, disallows administrator bypass and is restricted to `main`. The steps below describe the process for later releases; they do not authorize another publication.

## Prepare a candidate

1. Update `src/agency_garden/_version.py`, `CHANGELOG.md` and `CITATION.cff` together.
2. Run the checks in `CONTRIBUTING.md`. CI tests supported Python versions and operating systems, builds documentation and verifies the installed distributions.
3. Inspect the source archive and wheel. Confirm no credentials, generated runs or private research records are included.
4. Push a candidate branch and wait for the `release-check` aggregate CI check before merging its pull request. Branches in this repository are public; keep sensitive material out of commits. Retain the exact commit and archive hashes. Do not move an existing tag or replace historical artifacts.
5. Only after a separate release decision, create the matching tag and release. A public GitHub repository does not require a PyPI upload or a hosted documentation site.

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

Prepare the `pypi` GitHub environment, restricted to the default branch used to dispatch the workflow. Where the account plan supports it, require a maintainer reviewer and disable administrator bypass. Do not enable publishing as part of this setup.

Publication additionally requires all of these deliberate steps:

1. Explicit authorization for the particular package version, commit and PyPI destination.
2. The repository is public and the manual workflow is dispatched from `main`.
3. Set repository variable `PYPI_APPROVED_COMMIT` to the exact 40-character source commit, and `PYPI_PUBLISH_ENABLED` to `true`.
4. Re-enable the otherwise disabled Publish workflow, and dispatch it with an existing matching version tag.
5. The preparation job resolves that tag once and rejects any mismatch with the approved commit. CI and publication both use that immutable commit, not a moving tag.
6. After the upload, disable the workflow and reset the enable variable. Keep approval narrow and time-bounded. The workflow requests a short-lived PyPI credential through GitHub OIDC; no long-lived PyPI token belongs in this repository.

After configuring PyPI, run the **Publish to PyPI** workflow from GitHub Actions and supply the existing release tag. It runs the complete reusable validation workflow, checks that tag and package version match, builds distributions, and publishes the validated artifacts. If PyPI setup is incomplete, publication fails; a GitHub release alone does not make the package installable from PyPI.

The manual workflow also supports retrying a failed publication. PyPI versions cannot be overwritten. If a version already exists, inspect its files and provenance before changing anything; do not silently replace or skip files. After the first successful PyPI upload, switch installation examples to the index and update publication status in the documentation.

## Verify publication

Use a new virtual environment outside the checkout:

```bash
python -m pip install --pre 'agency-garden==0.1.0a3'
agency-garden --version
agency-garden init commons fresh-study
agency-garden run fresh-study/experiment.toml --output fresh-study/run
agency-garden verify fresh-study/run
```

Retain the published wheel and source archive with the tag. Research users should pin the version and record their complete environment because dependency and Python changes affect resume identity.

Official references: [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/) and [creating a pending publisher](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/).
