# ALAS Environment & Launcher Setup (Feb 2026)

## Overview
The ALAS environment has been modernized to support **Python 3.9** (specifically CPython 3.9.25) while maintaining compatibility with the project's legacy structure. The launcher scripts have been rewritten for robustness, portability, and automatic environment detection.

## Changes

### 1. Robust Launchers
Two unified launcher scripts have been implemented:
- **`start_alas.bat`** (Root): The primary entry point.
- **`alas_wrapped\alas.bat`** (Inner): A consistent internal entry point.

**Features:**
- **Dynamic Python Detection:** Automatically checks for `.venv` or `venv` within the `alas_wrapped` directory. Falls back to system `python` if no virtual environment is found.
- **Configurable Entry:** Supports an optional configuration name as the first argument (e.g., `start_alas.bat MyConfig`). Defaults to `PatrickCustom` if available, otherwise `alas`.
- **Improved Logic:** Uses nested `if-else` blocks to avoid common Windows Batch execution flow bugs.
- **Portability:** Uses relative paths (`%~dp0`) throughout to ensure it works regardless of where the project folder is moved.

### 2. Python 3.9 Compatibility
The project originally targeted Python 3.7. To run successfully on Python 3.9, the following adjustments were made to `alas_wrappedequirements.txt`:

- **Dependency Relaxation:** Strict version pins for build-heavy libraries were removed or commented out to allow `pip` to install compatible binary wheels for Python 3.9.
- **Affected Packages:**
    - `av` (commented out strict pin)
    - `numpy` (commented out strict pin)
    - `scipy` (commented out strict pin)
    - `cnocr` (unpinned to allow version resolution)
    - `gluoncv`, `mxnet`, `opencv-python`, `matplotlib`, `pillow` (unpinned to prevent downstream version conflicts)

### 3. Virtual Environment
A dedicated virtual environment has been established:
- **Location:** `alas_wrapped\.venv`
- **Python Version:** 3.9.25
- **Status:** Verified working with `import check` for `uiautomator2` and `cv2`.

## Maintenance
If dependencies need to be re-installed, ensure you are using the relaxed `requirements.txt`. Avoid re-pinning `numpy` or `scipy` to ancient versions (< 1.20) as they lack Python 3.9 binary support on Windows.
