# Assistant setup notes

This project uses uv for Python environment management.

## Quick start (Windows PowerShell)

- Ensure uv is installed and on PATH
  - Check: `uv --version`
- Create and sync the virtual environment
  - `uv venv .venv` (uses your default Python; to force 3.7: `uv venv --python "C:\\Python37\\python.exe" .venv`)
  - `uv pip sync -p .venv requirements.txt`
- Launch the ALAS Dashboard
  - `./start_alas.ps1`

## Notes

- The launcher (`start_alas.ps1`) automatically:
  - Stops any existing instance for a clean start
  - Ensures a venv exists; if missing and `uv` is available, it will create `.venv` and run `uv pip sync`
  - Starts the GUI with the venv Python
  - Opens the dashboard in Firefox if available (fallback to Chrome or default)
- Configuration:
  - Runtime behavior is configured in `config/alas.json` and `config/PatrickConfig.json`
  - Deployment knobs (ADB path, web UI port) are in `config/deploy.yaml`
- Web UI: http://localhost:22267/
