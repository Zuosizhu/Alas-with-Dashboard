# Agents and local dev

This repository is ready to run locally using the uv toolchain for Python environments.

## Environment

- Manager: [uv](https://docs.astral.sh/uv/)
- Venv location: `.venv` at the repo root
- Python baseline: 3.7-compatible (per `requirements.txt`) — if Python 3.7 is installed at `C:\Python37\python.exe`, the launcher will prefer it when bootstrapping.

### One-time setup

- Install uv and ensure it’s on PATH (verify with `uv --version`)
- Create and sync the environment:
  - `uv venv --python "C:\\Python37\\python.exe" .venv`  (or `uv venv .venv` to use your default Python)
  - `uv pip sync -p .venv requirements.txt`

## Running

- Start dashboard: `./start_alas.ps1`
- Stop dashboard: `./stop_alas.ps1`

The launcher will:
- Stop any existing instance
- Ensure the venv exists (and bootstrap it with uv if missing)
- Launch the GUI (`gui.py`) using the venv Python
- Open the Web UI in Firefox when available (fallback to Chrome or default)

## Ports and ADB

- Web UI: http://localhost:22267/
- ADB: configured in `config/deploy.yaml` (defaults to MEmu ADB path)

## Updating dependencies

- Edit `requirements-in.txt` and regenerate `requirements.txt` with your preferred workflow, then:
- Sync the environment: `uv pip sync -p .venv requirements.txt`
