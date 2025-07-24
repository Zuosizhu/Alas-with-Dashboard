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

The project has been modernized to Python 3.10+ with modern syntax:

```bash
# Optional code formatting (low priority)
black .

# Optional linting (low priority)
ruff check . --fix
```

## Current Development Status

### Completed Work
- ✅ **Python Modernization**: Successfully migrated from Python 3.7 to Python 3.10+ (300+ files updated)
- ✅ **OCR System Replacement**: Replaced broken cnocr with flexible multi-backend system (EasyOCR, Tesseract, SimpleOCR fallback)
- ✅ **LLM Vision Integration**: Implemented Gemini Flash 2.5 vision system with parallel analysis alongside traditional template matching
- ✅ **Windows Compatibility**: Fixed logger Unicode issues that prevented ALAS execution
- ✅ **Android Device Setup**: Configured MEmu emulator connection (127.0.0.1:21503) for live testing

### Current Phase: Ollama Local Vision Integration
- 🔄 **Setting up llava-phi3 model**: Optimized for RTX 4050 Ti hardware
- 🔄 **Local inference backend**: Adding ollama support as alternative to cloud-based Gemini API
- 📋 **Next**: Test LLM integration with real Azur Lane gameplay scenarios

### System Status
- **Branch**: `LLMRecognition` (up to date with remote)
- **OCR**: Multi-backend system functional (EasyOCR recommended)
- **Device Connection**: MEmu emulator configured and working
- **Configuration**: Direct file editing approach (bypassing problematic web interface)
- **Dependencies**: Modern Python 3.10+ with cleaned requirements

## Configuration Files

### Core Configuration
- **config/template.json**: Default task configurations
- **config/deploy.yaml**: Deployment settings (ADB path: ./platform-tools/adb.exe, auto-update disabled)
- **config/alas.json**: ALAS instance configuration (device serial, server settings)
- **config/argument/args.json**: Argument specifications for all modules
- **config/argument/task.yaml**: Task definitions and groupings

### Vision System Configuration
- **config/vision_llm_config.py**: Gemini Flash 2.5 API configuration
- **config/vision_ollama_config.py**: Ollama local inference configuration (llava-phi3 model)

## Common Issues

### OCR Not Working
- Install an OCR backend: `pip install easyocr` or install Tesseract
- Without OCR, ALAS runs but returns empty strings for text

### Device Connection Failed
- Check ADB is installed and in PATH
- Try `adb devices` to verify connection
- Use `python -m uiautomator2 init` for uiautomator2 setup

### Unicode Errors on Windows
- ✅ **Fixed**: Logger Unicode issues resolved by replacing box-drawing characters with ASCII equivalents

### Testing LLM Vision Integration
- Start MEmu emulator with Azur Lane
- Run ALAS with `python alas.py` 
- Check `logs/vision_llm.log` for comparative analysis data
- Monitor both traditional template matching and LLM vision results