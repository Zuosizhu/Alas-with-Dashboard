# Poetry Environment Setup for AzurLaneAutoScript

This document describes how to set up the development environment using Poetry for the AzurLaneAutoScript project.

## Prerequisites

1. **Python 3.7** (Required - all dependencies are pinned to versions compatible with Python 3.7)
2. **Poetry** (install with `pip install poetry`)
3. **Visual C++ Build Tools** (for Windows users) - Required for compiling some dependencies

## Installation Steps

### 1. Install Python 3.7

First, ensure you have Python 3.7 installed. You can download it from:
- Windows: https://www.python.org/ftp/python/3.7.9/python-3.7.9-amd64.exe
- Or use pyenv/pyenv-win to manage multiple Python versions

### 2. Install Poetry

Using Python 3.7:
```bash
python3.7 -m pip install poetry
```

### 3. Configure Poetry (Optional)

To create virtual environments in the project directory:
```bash
poetry config virtualenvs.in-project true
```

### 4. Install Dependencies

Navigate to the project directory and ensure Poetry uses Python 3.7:
```bash
cd "ALAS Give Up"
poetry env use python3.7
poetry install
```

If you encounter build errors for packages like `lz4`, `pillow`, or `pyzmq`, you may need to:

#### For Windows:
- Install Visual C++ Build Tools from: https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022
- Or install pre-built wheels manually:
  ```bash
  poetry run pip install lz4 --prefer-binary
  ```

#### For Linux/macOS:
- Ensure you have build essentials installed:
  ```bash
  # Ubuntu/Debian
  sudo apt-get install build-essential python3-dev
  
  # macOS
  xcode-select --install
  ```

### 5. Activate the Virtual Environment

```bash
poetry shell
```

Or run commands with:
```bash
poetry run python alas.py
```

## Dependency Notes

The `pyproject.toml` has been configured to use exact versions from the original requirements.txt to ensure compatibility:

1. **Python Version**: Python 3.7 is required for all dependencies to work correctly
2. **All Dependencies**: Using exact versions from the original requirements.txt
3. **OCR Dependencies**: `cnocr` (1.2.2) and `mxnet` (1.6.0) are included and will work with Python 3.7

## Running the Application

After installation, you can run:
```bash
poetry run python alas.py
```

Or with the GUI:
```bash
poetry run python gui.py
```

## Troubleshooting

### Build Errors

If you encounter build errors, try installing packages with pre-built wheels:
```bash
poetry run pip install --upgrade pip
poetry run pip install lz4 pillow pyzmq --prefer-binary
```

### OCR Functionality

The OCR dependencies (`cnocr` and `mxnet`) are included and will work properly with Python 3.7.

### Alternative: Using pip with requirements.txt

If Poetry installation fails, you can fall back to the original pip installation:
```bash
pip install -r requirements.txt
```

## Development

To add new dependencies:
```bash
poetry add package-name
```

To add development dependencies:
```bash
poetry add --group dev package-name
```

To update dependencies:
```bash
poetry update
```

## Benefits of Using Poetry

1. **Dependency Resolution**: Poetry automatically resolves dependency conflicts
2. **Lock File**: Ensures reproducible builds across different environments
3. **Virtual Environment**: Automatically manages virtual environments
4. **Modern Standards**: Uses pyproject.toml following PEP 517/518
5. **Version Management**: Easy to specify compatible version ranges