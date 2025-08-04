# ALAS Environment Setup Guide

## Quick Start (Recommended)

### Step 1: Install Python 3.7

#### Option A: Automatic Installation (Windows)
Run the PowerShell script:
```powershell
powershell -ExecutionPolicy Bypass -File install_python37.ps1
```

#### Option B: Manual Installation
Download and install from: https://www.python.org/ftp/python/3.7.9/python-3.7.9-amd64.exe
**Important**: Check "Add Python to PATH" during installation!

### Step 2: Install Visual C++ Build Tools (if needed)
Some packages require compilation. If you get build errors, install:
https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022

### Step 3: Setup ALAS Environment
Run the setup script:
   ```
   setup_environment.bat
   ```

2. This will:
   - Create a virtual environment
   - Install all dependencies
   - Activate the environment

### Manual Setup (All Platforms)

1. Create virtual environment:
   ```bash
   python -m venv venv
   ```

2. Activate virtual environment:
   - Windows: `venv\Scripts\activate.bat`
   - Linux/Mac: `source venv/bin/activate`

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running ALAS

1. Activate the virtual environment (if not already activated):
   ```bash
   venv\Scripts\activate.bat
   ```

2. Run ALAS:
   ```bash
   python alas.py
   ```

   Or with GUI:
   ```bash
   python gui.py
   ```

## Why Python 3.7?

The project uses specific versions of dependencies that were compiled for Python 3.7:
- `numpy==1.16.6` - doesn't support newer Python
- `scipy==1.4.1` - requires compatible numpy
- `mxnet==1.6.0` - OCR dependency, only works with Python 3.7
- `cnocr==1.2.2` - OCR functionality

Using a different Python version will cause compatibility issues!

## Troubleshooting

### "python" command not found
- Make sure Python 3.7 is installed and added to PATH
- Try using `python3.7` or `py -3.7` instead

### Build errors during installation
- Install Visual C++ Build Tools: https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022
- Select "Desktop development with C++" workload

### OCR not working
- Ensure you're using Python 3.7
- Check that mxnet and cnocr installed successfully

## Alternative: Using Poetry (Advanced)

If you prefer Poetry, see `POETRY_SETUP.md`. However, the simple venv approach above is recommended as it:
- Uses the tested requirements.txt directly
- Doesn't require additional tools
- Is simpler to troubleshoot