# Capture & Replay Infrastructure

> Deterministic fixture recording and offline replay for validating ALAS workflows without a live emulator.

## Overview

The capture/replay system has two halves:

1. **Recording** — Intercepts device calls (screenshot, click, swipe) during a live ALAS run and writes timestamped events + images to disk.
2. **Replay** — Feeds those captured images back through a mock device at CPU speed, validating that the identical action sequence is produced.

This enables regression testing of state-machine logic without hardware, and produces training data for future VLM integration.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│              Live ALAS Session                       │
│  (alas_wrapped runtime connected to emulator)       │
│                                                     │
│  DevicePatchSession monkey-patches:                 │
│    device.screenshot → save PNG + log event         │
│    device.click      → log target/area + forward    │
│    device.swipe      → log endpoints + forward      │
│                                                     │
│  ScenarioRecorder writes:                           │
│    tests/fixtures/<name>/manifest.jsonl             │
│    tests/fixtures/<name>/images/0001.png ... NNNN.png│
└─────────────────────────────────────────────────────┘
                        │
                        ▼  fixture on disk
┌─────────────────────────────────────────────────────┐
│              Offline Replay Test                     │
│  (no emulator required)                             │
│                                                     │
│  MockDevice reads manifest + images                 │
│  patched_time() controls SimulatedClock             │
│  ReplayDeviationError on sequence mismatch          │
└─────────────────────────────────────────────────────┘
```

## File Locations

| Component | File | Purpose |
|-----------|------|---------|
| Recorder | `alas_wrapped/dev_tools/record_scenario.py` | `ScenarioRecorder` + `DevicePatchSession` |
| Mock device | `agent_orchestrator/replay/mock_device.py` | `MockDevice`, `SimulatedClock`, `ReplayManifest` |
| Time control | `agent_orchestrator/replay/time_control.py` | `patched_time()` context manager |
| Replay tests | `agent_orchestrator/test_login_replay.py` | Pytest-based replay validation |
| Live capture | `agent_orchestrator/wander_capture.py` | Example: record a full reward workflow |
| Live smoke | `agent_orchestrator/smoke_test_live.py` | Verify ALAS context works against emulator |

## Fixture Format

Each recorded scenario lives under `tests/fixtures/<scenario_name>/`:

```
tests/fixtures/login_success/
├── images/
│   ├── 0001.png
│   ├── 0002.png
│   └── 0003.png
└── manifest.jsonl
```

### manifest.jsonl Schema

Each line is one JSON event. Three event types:

**Screenshot event:**
```json
{
  "index": 1,
  "event": "screenshot",
  "timestamp": 1708600000.100,
  "frame": 1,
  "image": "0001.png"
}
```

**Click event:**
```json
{
  "index": 2,
  "event": "action",
  "timestamp": 1708600000.101,
  "action": "click",
  "target": "GOTO_MAIN",
  "area": [1213, 18, 1245, 49]
}
```

**Swipe event:**
```json
{
  "index": 3,
  "event": "action",
  "timestamp": 1708600001.200,
  "action": "swipe",
  "target": "SWIPE",
  "start_area": [190, 190, 210, 210],
  "end_area": [230, 230, 250, 250]
}
```

## Recording a Scenario

### Programmatic (recommended)

```python
from dev_tools.record_scenario import ScenarioRecorder, DevicePatchSession
from alas_mcp_server import ALASContext

ctx = ALASContext('alas')
recorder = ScenarioRecorder('my_scenario')

with DevicePatchSession(device=ctx.script.device, recorder=recorder):
    ctx.script.reward()  # or any workflow
```

### CLI

```bash
cd alas_wrapped
python -m dev_tools.record_scenario login_flow --config alas --method handle_app_login
```

## Running Replay Tests

```bash
cd agent_orchestrator
uv run pytest test_login_replay.py -v
```

## Monkey-Patching Inventory

The system uses several monkey-patching strategies:

| Layer | What's Patched | Mechanism | Restored? |
|-------|---------------|-----------|-----------|
| Recording | `device.screenshot/click/swipe` | `types.MethodType` rebinding | Yes (context manager `__exit__`) |
| Replay | `time.time()`, `time.sleep()` | `unittest.mock.patch` via ExitStack | Yes (context manager) |
| Replay | `module.base.timer.*` | `unittest.mock.patch` (optional, silent fail) | Yes |
| WebUI | `ThreadPoolExecutor`, `mimetypes` | Direct replacement | Permanent |
| ADB | `AdbClient._connect` | Compatibility shim | Permanent |

## Telemetry Correlation

All logging channels share timestamps that can be cross-referenced:

| Channel | Location | Correlation Key |
|---------|----------|-----------------|
| ALAS main log | `alas_wrapped/log/YYYY-MM-DD_*.txt` | Line timestamp (ms) |
| Scheduler JSONL | `alas_wrapped/log/schedule_status.jsonl` | `ts` field (ISO) |
| Login trace JSONL | `alas_wrapped/log/login_trace.jsonl` | `ts` field (ISO) |
| Scenario manifest | `tests/fixtures/*/manifest.jsonl` | `timestamp` (Unix epoch) |
| Error snapshots | `alas_wrapped/log/error/<millis>/` | Directory name (ms) |
| Watchdog log | User-specified path | `ts` + `config` fields |

To build a complete timeline of a run, convert all timestamps to the same format and merge-sort the streams.

## Known Gaps

1. **No sleep/wait capture** — Timing-dependent logic invisible to replay.
2. **No error state capture** — Crashes abort recording silently; no replay of recovery paths.
3. **No manifest versioning** — No forward-compatibility if schema changes.
4. **Point tuple area extraction** — `[x, y, x, y]` degenerate areas may cause validation issues during replay.
5. **Recorder doesn't capture MCP tool calls** — Only raw device interactions are recorded.

## Next Steps

- [ ] Add error-state capture (record partial scenarios on crash)
- [ ] Add manifest schema version field
- [ ] Record MCP-level tool invocations alongside device actions
- [ ] Auto-capture replay fixtures on `GameStuckError` for postmortem replay
- [ ] Add swipe validation tests to `test_login_replay.py`
