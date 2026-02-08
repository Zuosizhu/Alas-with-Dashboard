# Environment & Launcher Setup

> **Status**: Verified Feb 2026
> **Scope**: `alas_wrapped` development and execution environment

This document explains the modernization of the ALAS environment to support **Python 3.9** and the improved launcher architecture for the monorepo.

## 1. Unified Launchers

The monorepo provides two entry points for launching the ALAS Web UI and core logic. These scripts are designed for portability and automatic environment detection.

| Launcher | Location | Purpose |
| :--- | :--- | :--- |
| `start_alas.bat` | Root (`/`) | Primary user entry point. Handles root-level context. |
| `alas.bat` | `alas_wrapped/` | Inner entry point for focused ALAS development. |

### Features
- **Dynamic Python Detection**: Automatically checks for virtual environments in the following order:
  1. `alas_wrapped/.venv`
  2. `alas_wrapped/venv`
  3. System `python` (Fallback)
- **Configurable Entry**: Both scripts support an optional configuration name as the first argument:
  ```bash
  start_alas.bat PatrickCustom
  ```
- **Portability**: Uses relative pathing (`%~dp0`) to remain functional if the project directory is moved.
- **Robust Execution**: Uses nested logic to prevent common Windows Batch execution flow bugs.

---

## 2. Python 3.9+ Compatibility

While the legacy ALAS documentation recommends Python 3.7.6, the monorepo has been updated to support **Python 3.9** (specifically verified with CPython 3.9.25). 

### Why this was needed
Ancient versions of core libraries (e.g., `numpy 1.16.6`, `scipy 1.4.1`) originally pinned by ALAS do not have pre-compiled binary wheels for Python 3.9+ on Windows. Compiling them from source is difficult and prone to failure.

### The Solution: Relaxed Pins
To maintain compatibility with modern Python without losing functionality, we relaxed strict version pins in `alas_wrapped/requirements.txt`:

| Package | Status | Reasoning |
| :--- | :--- | :--- |
| `av`, `numpy`, `scipy` | Commented out | Allow `pip` to install the latest compatible binary wheel for Python 3.9. |
| `cnocr`, `gluoncv`, `mxnet` | Unpinned | Prevent these libraries from forcing ancient, incompatible sub-dependencies. |
| `opencv-python`, `pillow` | Unpinned | Ensure consistent binary compatibility across the stack. |

---

## 3. Maintenance Procedures

### Establishing the Venv
To create a fresh environment compatible with this setup:
1. Ensure Python 3.9 is installed.
2. Run the following commands (or use the logic in `start_alas.bat`):
   ```bash
   cd alas_wrapped
   py -3.9 -m venv .venv
   .venv\Scripts\pip install -r requirements.txt
   ```

### Verification
A healthy environment must successfully pass these imports:
```python
import uiautomator2
import cv2
import cnocr
```
