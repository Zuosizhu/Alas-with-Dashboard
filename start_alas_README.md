# ALAS Launcher

`start_alas.bat` at repository root is the canonical Windows launcher for this repo.

## Canonical Entry

```batch
start_alas.bat [options] [config_name]
```

Default behavior is wrapped stack (`alas_wrapped`).
Use `--upstream` only when you intentionally want legacy upstream launch flow.

## Supported Options

| Option | Description |
|--------|-------------|
| `--electron` | Launch wrapped Electron app instead of browser UI |
| `--force` | Stop existing ALAS process and restart |
| `--benchmark` | Run ALAS benchmark for screenshot/control methods |
| `--silent` | Non-interactive run for scheduled usage |
| `--no-browser` | Skip browser auto-open |
| `--attach` | Attach to existing instance only; do not start |
| `--upstream` | Delegate launch to `upstream_alas` |

## Examples

```batch
start_alas.bat
start_alas.bat PatrickCustom
start_alas.bat --force
start_alas.bat --silent --no-browser
start_alas.bat --electron
start_alas.bat --upstream
```

## Compatibility Wrappers

- `alas_wrapped/alas.bat` delegates to `start_alas.bat`.
- `alas_wrapped/deploy/launcher/Alas.bat` delegates to `start_alas.bat`.

No launcher logic should be maintained in wrapper scripts.
All launcher changes should be made in `start_alas.bat`.
