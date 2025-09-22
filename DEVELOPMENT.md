# Development setup

This project includes a recommended pre-commit configuration to keep code formatted and reduce accidental commits of generated or temporary files.

## Install pre-commit (recommended)

On Windows (PowerShell), using the project's Python environment or your system Python, run:

```powershell
python -m pip install --user pre-commit
# or, if you use a virtualenv:
# python -m pip install pre-commit
```

Then inside the repo root:

```powershell
cd 'c:\Users\user\Desktop\songlab_advanced'
python -m pre_commit install
# To run hooks across all files once:
python -m pre_commit run --all-files
```

If `python -m pre_commit` doesn't work, try `pre-commit` directly after installing it to your PATH.

## Notes
- We added `.pre-commit-config.yaml` with basic hooks: trailing-whitespace, EOF fixer, Black, isort, and ESLint (JS/JSX).
- If you don't want ESLint hooks to run, remove or adjust the ESLint section in `.pre-commit-config.yaml`.
- The `.gitignore` was updated to ignore local frontend temp helper scripts and audio test data.
