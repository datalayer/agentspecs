# Making a new release of agentspecs

## Automated release (tags)

A pushed `v*` tag publishes that version to [PyPI](https://pypi.org/project/agentspecs/)
through [`.github/workflows/release.yaml`](.github/workflows/release.yaml), with trusted
publishing: no token is stored in the repository.

1. Bump `__version__` in `agentspecs/__version__.py`, open a pull request and merge it to
   `main`.
2. Tag the merge commit with the same version and push the tag:

   ```bash
   git checkout main && git pull
   git tag v0.0.7
   git push origin v0.0.7
   ```

The workflow checks that the tag equals `__version__` (it stops otherwise), then runs
[`ci.yaml`](.github/workflows/ci.yaml) — the tests on Python 3.10 to 3.13, and the build: the
sdist and the wheel with `python -m build`, `twine check`, the YAML specs in the wheel, and
an import of the installed wheel. Only when all of that passes does it publish that sdist
and wheel with `pypa/gh-action-pypi-publish`, in the `pypi` environment.

The same `ci.yaml` runs on every pull request and every push to `main`.

PyPI never accepts the same version twice: a failed run can be re-run from the Actions tab,
but a change after a publish needs a new version and a new tag.

### One-time setup

On <https://pypi.org/manage/project/agentspecs/settings/publishing/>, add a GitHub trusted
publisher:

- Owner: `datalayer`
- Repository name: `agentspecs`
- Workflow name: `release.yaml`
- Environment name: `pypi`

The `pypi` environment exists in the repository settings (_Settings → Environments_);
protection rules added there gate every upload.

## Manual release

```bash
pip install build twine
python -m build
twine upload dist/*
```
