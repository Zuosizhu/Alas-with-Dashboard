# ALAS Launcher

Canonical root launcher for running ALAS from this repository.
This is the **single normal-run entrypoint**.

## Usage

```batch
start_alas.bat [options] [config_name]
```

`start_alas.bat` starts the wrapped, MCP-augmented stack by default.
Use `--upstream` when you need the legacy launcher.

## Options

| Option | Description |
|--------|-------------|
| `--electron` | Launch Electron app (wrapped) instead of browser UI |
| `--force` | Kill existing ALAS and restart fresh |
| `--benchmark` | Run ALAS built-in benchmark to test screenshot/control methods |
| `--silent` | No prompts, suitable for scheduled tasks |
| `--no-browser` | Don't auto-open browser on start |
| `--attach` | Only attach to existing, don't start new |
| `--upstream` | Use legacy `upstream_alas` launcher flow |

## Examples

```batch
:: Start default config (PatrickCustom if present)
start_alas.bat

:: Start Electron app (wrapped)
start_alas.bat --electron

:: Force restart even if running
start_alas.bat --force

:: Run benchmark to find fastest screenshot method
start_alas.bat --benchmark

:: Silent background start
start_alas.bat --silent --no-browser

:: Specific config
start_alas.bat MyCustomConfig

:: Legacy upstream startup
start_alas.bat --upstream
```

## Important notes

- `start_alas.bat` is the only launcher users should use for normal runs.
- Use `--upstream` only if you specifically need the legacy `upstream_alas` path.

## What I ran

I ran:

```batch
start_alas.bat --silent --no-browser --attach
```

It started and reached the wrapped launch path correctly, then exited because `gui.py` hit a config JSON parse failure in `module/config`.
That runtime error is separate from launcher selection/dispatch logic.

## Benchmark Mode

Uses ALAS's built-in `module/daemon/benchmark.py` to test:

**Screenshot methods:**
- `ADB` - Standard ADB
- `ADB_nc` - ADB with netcat
- `uiautomator2` - uiautomator2 framework
- `aScreenCap` - aScreenCap (usually fastest)
- `aScreenCap_nc` - aScreenCap with netcat
- `DroidCast` / `DroidCast_raw` - DroidCast methods
- `nemu_ipc` - MEmu IPC (if available)
- `ldopengl` - LDPlayer OpenGL (if available)

**Control methods:**
- `ADB` - Standard ADB tap/swipe
- `uiautomator2` - uiautomator2 click
- `minitouch` - minitouch (fast)
- `MaaTouch` - MaaTouch (preferred if available)

Results show timing and speed rating (Insane Fast / Ultra Fast / etc.).

## Process Detection

Wrapped mode checks:
1. **GUI Process** - web UI server (`gui.py`)
2. **Bot Process** - scheduler/automation process (`alas.py` / `AzurLaneAutoScript`)
3. **Web Port** - TCP 22267 listener

ALAS is considered running only when GUI process and web port are active.
