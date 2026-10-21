# Release procedure and publication state

Initial version: **0.1.0**. **PyPI: NOT PUBLISHED** until an upload is independently verified.
The release workflow builds validated artifacts when a non-prerelease GitHub release with a `v` tag is published.
A separate `github-assets` job automatically attaches the verified wheel and sdist to that GitHub release.
Only this asset-upload job receives `contents: write`; it uses GitHub's short-lived workflow token.
The PyPI upload job stays disabled unless repository variable `PYPI_PUBLISH_ENABLED` is exactly `true`.

## First publication

1. Confirm the normalized project name `framebond` and the irreversible initial PyPI publication with the owner.
2. Recheck [PyPI's JSON endpoint](https://pypi.org/pypi/framebond/json). A 404 does not guarantee registration rights or name availability.
3. Sign in to the owner's authorized personal PyPI account. At [Publishing](https://pypi.org/manage/account/publishing/), add a **pending publisher** with these exact values:

| Field | Value |
|---|---|
| PyPI project name | `framebond` |
| GitHub owner | `giovannyTorres` |
| GitHub repository | `framebond` |
| Workflow filename | `release.yml` |
| Environment | `pypi` |

4. Create GitHub environment `pypi` in this repository. If available on the account, require owner approval and restrict deployments to release tags. Add the repository variable only after these checks and confirmation.
5. Ensure CI is green. Publish the GitHub release `v0.1.0` from the reviewed main commit. Only the isolated publish job receives `id-token: write`; no PyPI token is stored.
6. If the release was created before enabling uploads, rerun the Release workflow only after enabling and reviewing the publisher settings.
7. Verify the public PyPI project and install `framebond==0.1.0` in a fresh environment from the public index. Update this publication state only after that succeeds.

## Future versions

Update `[project].version`, the module's `__version__`, and CHANGELOG.md together. Run the checks in CONTRIBUTING.md, including clean wheel and sdist installations.
Review the diff, push the commit, wait for CI, then publish a GitHub release whose tag is exactly `v` plus the package version.
Review environment approval before upload. Existing Trusted Publisher settings can be reused for this exact repository, workflow, and environment.
PyPI cannot replace files of an already uploaded version; fixes need a new version.

## References and action verification

- [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
- [Creating a project with OIDC](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)
- [Using a publisher](https://docs.pypi.org/trusted-publishers/using-a-publisher/)
- Workflow actions are pinned to upstream tag commit SHAs verified on 2026-10-21: checkout 7.0.1, setup-python 7.0.0, upload-artifact 7.0.2, download-artifact 8.0.2, pypa/gh-action-pypi-publish 1.14.2.

No external credentials, account creation, environment approval, or initial upload is implied by this file.
