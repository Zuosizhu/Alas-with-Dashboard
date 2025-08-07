# ALAS Configuration System Documentation

## Overview

ALAS (Azur Lane Auto Script) uses a sophisticated multi-layer configuration system that allows users to control all aspects of the bot's behavior through a web-based GUI. This document provides a comprehensive understanding of how the configuration system works.

## Architecture

### 1. Configuration Storage

The configuration system uses multiple file types and locations:

- **Runtime Configuration**: `config/alas.json`
  - Stores current configuration values
  - Contains dashboard data (resources, statistics)
  - Updated dynamically during bot operation

- **Configuration Templates**: 
  - `config/template.json` - Default configuration template
  - `config/template.maa.json` - MAA-specific template
  - `config/deploy.yaml` - Deployment configuration
  - Various platform-specific templates (Docker, Linux, AidLux)

### 2. Configuration Definition System

The configuration structure is defined through a hierarchical YAML/JSON system:

- **`module/config/argument/argument.yaml`**
  - Master definition file for all configuration parameters
  - Defines parameter types, default values, and options
  - Structure: `ParameterGroup: { ParameterName: { properties... } }`

- **`module/config/argument/task.yaml`**
  - Groups parameters into logical task categories
  - Defines which parameters appear together in the GUI
  - Maps tasks to their required configuration groups

- **`module/config/argument/menu.json`**
  - Defines the GUI menu structure
  - Organizes tasks into collapsible menu sections
  - Controls the navigation hierarchy

- **`module/config/argument/args.json`**
  - JSON representation of arguments with type information
  - Used for dynamic form generation in the web interface
  - Includes validation rules and display properties

### 3. Internationalization

- **Location**: `module/config/i18n/`
- **Supported Languages**:
  - English (en-US)
  - Simplified Chinese (zh-CN)
  - Traditional Chinese (zh-TW)  
  - Japanese (ja-JP)
- **Structure**: JSON files containing translations for all UI elements and help text

## Configuration Categories

### Core Categories

1. **Alas** - Core system settings
   - Emulator configuration
   - Error handling
   - Performance optimization
   - Drop recording

2. **Farm** - Main campaign automation
   - Multiple farming profiles (Main, Main2, Main3)
   - Commission farming mode
   - Stage selection and clearing strategies

3. **Event** - Special event handling
   - Event stages configuration
   - Raid events
   - Hospital (Valley Hospital event)
   - Coalition events
   - War Archives

4. **EventDaily** - Daily event stages
   - Event stages A, B, C, D
   - SP stages
   - Daily raid configuration

5. **Reward** - Reward collection automation
   - Commission rewards
   - Tactical class
   - Research projects
   - Dorm management
   - Meowfficer collection
   - Guild operations

6. **DailyMission** - Daily activities
   - Daily missions
   - Hard mode stages
   - Exercise (PvP)
   - Shop purchases (frequent/once)
   - Shipyard construction
   - Gacha pulls
   - Freebies collection

7. **Opsi** - Operation Siren
   - General OpSi settings
   - Ash beacon coordination
   - Zone exploration
   - Shop purchases
   - Various OpSi-specific modes

8. **Tool** - Utility functions
   - Daemon mode
   - Benchmark tools
   - Game management utilities

## Key Configuration Groups

### Emulator Configuration
```yaml
Emulator:
  Serial: auto                    # Device serial or 'auto'
  PackageName: auto              # Game package name
  ScreenshotMethod: auto         # ADB, uiautomator2, aScreenCap, etc.
  ControlMethod: MaaTouch        # Input method for controlling game
  ScreenshotDedithering: false   # Image processing option
  AdbRestart: false              # Auto-restart ADB on failure
```

### Campaign Configuration
```yaml
Campaign:
  Name: "12-4"                   # Stage to farm
  Event: campaign_main           # Event type
  Mode: normal                   # normal/hard
  UseClearMode: true            # Use clearing mode
  UseFleetLock: true            # Lock fleet configuration
  UseAutoSearch: true           # Enable auto-search
  Use2xBook: false              # Use 2x reward books
  AmbushEvade: true             # Attempt to evade ambushes
```

### Fleet Management
```yaml
Fleet:
  Fleet1: 1                      # Fleet number (1-6)
  Fleet1Formation: double_line   # line_ahead, double_line, diamond
  Fleet1Mode: combat_auto        # Combat behavior
  Fleet1Step: 3                  # Movement range (2-5)
  Fleet2: 2                      # Boss fleet configuration
```

### Resource Management
```yaml
StopCondition:
  OilLimit: 1000                # Stop when oil drops below
  RunCount: 0                   # Number of runs (0 = infinite)
  MapAchievement: non_stop      # Achievement target
  StageIncrease: false          # Progress to next stage
  GetNewShip: false             # Stop on new ship drop
```

### Emotion/Morale System
```yaml
Emotion:
  Mode: calculate               # calculate, ignore, calculate_ignore
  Fleet1Control: prevent_yellow_face  # Morale threshold
  Fleet1Recover: not_in_dormitory    # Recovery method
  Fleet1Oath: false             # Oath bonus consideration
```

## Configuration Flow

1. **Definition Phase**
   - Parameters defined in YAML files
   - Type information and validation rules specified
   - Default values and options configured

2. **Code Generation**
   - `config_generated.py` created from YAML definitions
   - Type-safe configuration classes generated
   - Validation logic embedded

3. **GUI Presentation**
   - Web interface dynamically generates forms
   - Input types match parameter definitions
   - Real-time validation and feedback

4. **Runtime Application**
   - User changes trigger configuration updates
   - Changes saved to JSON configuration file
   - Bot reads configuration on task execution
   - Some changes apply immediately, others on restart

## Web GUI Integration

The configuration system is fully exposed through a PyWebIO-based web interface:

- **Dynamic Form Generation**: Forms created based on argument definitions
- **Type-Specific Controls**: 
  - Checkboxes for boolean values
  - Dropdowns for enum selections
  - Text inputs for strings/numbers
  - DateTime pickers for time values
- **Real-time Updates**: Changes immediately saved to configuration
- **Multi-language Support**: Interface adapts to user's language preference
- **Responsive Design**: Works on desktop and mobile devices

## Configuration Files Reference

| File | Purpose |
|------|---------|
| `config/alas.json` | Active configuration and runtime data |
| `module/config/argument/argument.yaml` | Parameter definitions |
| `module/config/argument/task.yaml` | Task groupings |
| `module/config/argument/menu.json` | GUI menu structure |
| `module/config/config.py` | Main configuration class |
| `module/config/config_generated.py` | Auto-generated config code |
| `module/webui/app.py` | Web interface implementation |

## Best Practices

1. **Backup Configurations**: Keep backups of `alas.json` before major changes
2. **Test Changes**: Test configuration changes on non-critical tasks first
3. **Resource Limits**: Always set appropriate oil/coin limits to prevent waste
4. **Fleet Setup**: Configure fleets properly before enabling automation
5. **Monitor Logs**: Check logs regularly to ensure configurations work as expected

## Advanced Features

- **Multiple Profiles**: Run different configurations by using different config files
- **Scheduled Tasks**: Configure tasks to run at specific times
- **Conditional Logic**: Some parameters enable/disable based on other settings
- **Override System**: Force specific values regardless of GUI settings
- **Hot Reload**: Many settings apply without restarting the bot

This configuration system provides complete control over ALAS behavior while maintaining ease of use through the web interface.