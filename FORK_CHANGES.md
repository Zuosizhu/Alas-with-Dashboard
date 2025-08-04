# ALAS Give Up - Fork Changes Documentation

## Overview
This is a customized fork of [AzurLaneAutoScript](https://github.com/LmeSzinc/AzurLaneAutoScript) with enhanced Windows setup experience.

## Custom Changes Made

### 1. Enhanced Windows Setup Scripts
This fork adds several custom batch scripts to simplify the installation process on Windows:

#### `setup_simple.bat` - One-Click Setup
- **Purpose**: Complete automated setup requiring no manual Python installation
- **Features**:
  - Downloads Python 3.7.9 embedded distribution (24MB)
  - Configures Python with pip support
  - Installs all ALAS dependencies automatically
  - Creates ready-to-use run scripts
  - No system PATH modifications required

#### `setup_environment.bat` - Virtual Environment Setup
- **Purpose**: Sets up ALAS with existing Python 3.7 installation
- **Features**:
  - Detects Python 3.7 installations
  - Creates isolated virtual environment
  - Installs dependencies in venv
  - Provides activation instructions

#### `setup_portable_python.bat` - Portable Python Setup
- **Purpose**: Downloads and sets up portable Python installation
- **Features**:
  - Downloads Python 3.7.9 embedded package
  - Configures pip in portable environment
  - Sets up virtual environment
  - Clean portable installation

### 2. Enhanced Run Scripts
Modified the standard run scripts to work with portable Python:

#### `run_alas.bat`
```bat
@echo off
echo Starting ALAS...
python-3.7.9-embed-amd64\python.exe alas.py
pause
```

#### `run_gui.bat`
```bat
@echo off
echo Starting ALAS GUI...
python-3.7.9-embed-amd64\python.exe gui.py
pause
```

### 3. Portable Python Distribution
- **Included**: Complete Python 3.7.9 embedded distribution in `python-3.7.9-embed-amd64/`
- **Benefits**: 
  - Self-contained installation
  - No system Python required
  - No conflicts with existing Python installations
  - Easy deployment and portability

### 4. User Experience Improvements
- **No Python Installation Required**: Users can run ALAS without installing Python system-wide
- **One-Click Setup**: `setup_simple.bat` handles everything automatically
- **Multiple Setup Options**: Three different setup methods for different user preferences
- **Error Prevention**: Scripts check for requirements and provide clear error messages

## Git Repository Setup

### Remote Configuration
```bash
# Upstream remote pointing to original repository
upstream    https://github.com/LmeSzinc/AzurLaneAutoScript.git (fetch)
upstream    https://github.com/LmeSzinc/AzurLaneAutoScript.git (push)
```

### Current Status
- **Base**: Latest upstream master (commit c287b8572)
- **Custom Commit**: 68de92e53 - "Initial commit: ALAS fork with custom Windows setup scripts"
- **Files Added**: 8,133 files committed (original ALAS + custom setup scripts + portable Python)

## Maintaining the Fork

### To Update from Upstream
```bash
# Fetch latest changes
git fetch upstream

# View what's new
git log --oneline HEAD..upstream/master

# Merge upstream changes (if no conflicts)
git merge upstream/master

# Or rebase your changes on top of upstream
git rebase upstream/master
```

### Custom Files to Preserve
When merging upstream changes, ensure these custom files are preserved:
- `setup_simple.bat`
- `setup_environment.bat` 
- `setup_portable_python.bat`
- Modified `run_alas.bat`
- Modified `run_gui.bat`
- `python-3.7.9-embed-amd64/` directory (entire portable Python installation)
- This documentation file (`FORK_CHANGES.md`)

## Installation Instructions for Users

### Option 1: One-Click Setup (Recommended)
1. Download this fork
2. Double-click `setup_simple.bat`
3. Wait for automatic setup to complete
4. Run ALAS using `run_alas.bat` or `run_gui.bat`

### Option 2: Use Existing Python 3.7
1. Ensure Python 3.7 is installed on your system
2. Run `setup_environment.bat`
3. Activate the virtual environment: `venv\Scripts\activate.bat`
4. Run ALAS: `python alas.py`

### Option 3: Portable Python Setup
1. Run `setup_portable_python.bat`
2. Follow the script instructions
3. Use the created virtual environment

## Benefits of This Fork
- **Beginner Friendly**: No technical knowledge required
- **Portable**: Entire installation can be moved between computers
- **Clean**: No system-wide Python installation required
- **Safe**: Isolated environment prevents conflicts
- **Automated**: Minimal user interaction required

## Version Information
- **Fork Created**: July 26, 2025
- **Base ALAS Version**: Latest master as of August 4, 2025
- **Python Version**: 3.7.9 (embedded)
- **Setup Scripts Version**: 1.0

---
*This fork maintains full compatibility with the original ALAS while adding Windows-specific convenience features.*
