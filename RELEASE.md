# Release procedure and publication state

Current version: **0.1.0**. **PyPI: PUBLISHED** at
[framebond 0.1.0](https://pypi.org/project/framebond/0.1.0/).
Installation from the public index was verified in a fresh environment, including
`pip check`, both executable examples, wheel hash and installed source identity.
The release workflow builds validated artifacts when a non-prerelease GitHub release with a `v` tag is published.
A separate `github-assets` job automatically attaches the verified wheel and sdist to that GitHub release.
Only this asset-upload job receives `contents: write`; it uses GitHub's short-lived workflow token.
The upload guard `PYPI_PUBLISH_ENABLED` is configured as `true`. The isolated
PyPI job uses the protected GitHub environment `pypi` and OIDC Trusted Publishing;
no PyPI token is stored.

## Configured Trusted Publisher

The owner approved the project name and initial publication. The publisher is
configured for these exact values:

| Field | Value |
|---|---|
| PyPI project name | `framebond` |
| GitHub owner | `giovannyTorres` |
| GitHub repository | `framebond` |
| Workflow filename | `release.yml` |
| Environment | `pypi` |

Only the isolated PyPI upload job receives `id-token: write`. Keep the publisher,
workflow and environment aligned when changing release infrastructure.

## Future versions

Update `[project].version`, the module's `__version__`, and CHANGELOG.md together. Run the checks in CONTRIBUTING.md, including clean wheel and sdist installations.
Review the diff, push the commit, wait for CI, then publish a GitHub release whose tag is exactly `v` plus the package version.
Review environment approval before upload. Existing Trusted Publisher settings can be reused for this exact repository, workflow, and environment.
After upload, verify the new public PyPI version and install it in a fresh
environment from the public index before recording publication success.
PyPI cannot replace files of an already uploaded version; fixes need a new version.

## References and action verification

- [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
- [Creating a project with OIDC](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)
- [Using a publisher](https://docs.pypi.org/trusted-publishers/using-a-publisher/)
- Workflow actions are pinned to upstream tag commit SHAs verified on 2026-10-21: checkout 7.0.1, setup-python 7.0.0, upload-artifact 7.0.2, download-artifact 8.0.2, pypa/gh-action-pypi-publish 1.14.2.

This file records the verified 0.1.0 publication and the procedure for future releases.
