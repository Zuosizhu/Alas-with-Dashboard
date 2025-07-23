# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

ALAS (AzurLaneAutoScript) is an automation bot for the Azur Lane mobile game. It uses computer vision and OCR to read game state and automate gameplay tasks.

## Running ALAS

```bash
# Install dependencies
pip install -r requirements.txt

# Run GUI (web interface on port 22267)
python gui.py

# Run CLI directly
python alas.py

# Install/update ALAS components
python -m deploy.installer
```

## Architecture

### Core Module Structure

The codebase follows a modular architecture where each game feature is implemented as a separate module:

- **module/base/**: Core utilities including decorators, timers, filters, and the critical `Button` class that represents UI elements
- **module/device/**: Device abstraction layer supporting multiple connection methods (ADB, uiautomator2, minitouch)
- **module/ocr/**: OCR system with flexible backend support (EasyOCR, Tesseract, or SimpleOCR fallback)
- **module/config/**: Configuration management, argument parsing, and i18n support
- **module/webui/**: PyWebIO-based web interface

### Key Architectural Patterns

1. **Screenshot-Based Automation**: The bot works by taking screenshots, analyzing them with OCR/image recognition, and sending touch commands
2. **Task System**: Each game activity (campaign, event, daily) is a separate task with its own module
3. **Button/Asset System**: UI elements are defined as `Button` objects with image assets for recognition
4. **Configuration-Driven**: Extensive YAML/JSON configuration system for tasks, schedules, and settings

### Important Classes and Concepts

- **AzurLaneAutoScript** (alas.py): Main orchestrator that runs tasks in a loop
- **ModuleBase**: Base class for all game modules, provides screenshot, click, and wait methods
- **Button**: Represents a clickable UI element with associated image assets
- **Config**: Global configuration object accessible throughout the codebase
- **Device**: Abstraction for Android device connection and control

## OCR System

The OCR system has been refactored to support multiple backends:

```python
# OCR automatically selects best available backend:
# 1. EasyOCR (best for game text)
# 2. Tesseract (good alternative)
# 3. SimpleOCR (placeholder, returns empty strings)

# Install OCR backend (optional):
pip install easyocr  # Recommended
# OR
pip install pytesseract  # Requires Tesseract binary
```

## Development Workflow

### Adding a New Task Module

1. Create a new directory under `module/` for your feature
2. Create asset images in `assets/<module_name>/`
3. Define UI buttons in your module
4. Implement logic extending `ModuleBase`
5. Add configuration in `config/argument/`

### Debugging

```bash
# Enable debug logging
python alas.py --debug

# Test OCR functionality
python test_ocr_simple.py

# Check device connection
python -m uiautomator2 init
```

### Code Style

The project currently uses Python 3.7.6 but is being modernized to Python 3.10+:

```bash
# Format code (after modernization)
black .

# Lint code (after modernization)
ruff check . --fix
```

## Current Development Status

### Active Work
- **Python Modernization**: Migrating from Python 3.7 to 3.10+ (tracked in PYTHON_MODERNIZATION_ISSUE.md)
- **OCR Migration**: Replaced broken cnocr with flexible backend system (see VISION_MODEL_OCR_PROPOSAL.md)

### Post-Merge Tasks
1. Apply stashed Python modernization changes
2. Update dependencies (remove cnocr/mxnet, add optional OCR backends)
3. Fix logger Unicode issues on Windows
4. Add comprehensive test suite

## Configuration Files

- **config/template.json**: Default task configurations
- **config/deploy.template.yaml**: Deployment settings (Git, Python, ADB paths)
- **config/argument/args.json**: Argument specifications for all modules
- **config/argument/task.yaml**: Task definitions and groupings

## Common Issues

### OCR Not Working
- Install an OCR backend: `pip install easyocr` or install Tesseract
- Without OCR, ALAS runs but returns empty strings for text

### Device Connection Failed
- Check ADB is installed and in PATH
- Try `adb devices` to verify connection
- Use `python -m uiautomator2 init` for uiautomator2 setup

### Unicode Errors on Windows
- Known issue with the logger and Unicode characters
- Temporary fix: Avoid Unicode in log messages