# ALAS Test Fixtures

This directory contains recorded screenshot/action sequences for deterministic replay testing.

## Fixture Structure

Each fixture is a subdirectory containing:

```
fixtures/
  <scenario_name>/
    manifest.jsonl    # Event log (screenshots + actions)
    images/           # Screenshot frames
      0001.png
      0002.png
      ...
```

## Manifest Format (JSON Lines)

Each line is a JSON object with one of the following structures:

### Screenshot Event
```json
{
  "index": 1,
  "event": "screenshot",
  "timestamp": 1708600000.100,
  "frame": 1,
  "image": "0001.png"
}
```

### Click Action Event
```json
{
  "index": 2,
  "event": "action",
  "timestamp": 1708600000.101,
  "action": "click",
  "target": "LOGIN_CHECK",
  "area": [90, 90, 150, 150]
}
```

### Swipe Action Event
```json
{
  "index": 3,
  "event": "action",
  "timestamp": 1708600001.100,
  "action": "swipe",
  "target": "SWIPE",
  "start_area": [190, 190, 210, 210],
  "end_area": [230, 230, 250, 250]
}
```

## Recording New Fixtures

Use the record_scenario.py tool:

```bash
python alas_wrapped/dev_tools/record_scenario.py <scenario_name> --config PatrickCustom
```

Options:
- `--config`: ALAS config name (default: "alas")
- `--method`: Device method to record (default: "handle_app_login")
- `--fixtures-root`: Output directory (default: "<repo_root>/tests/fixtures")

## Using Fixtures in Tests

```python
from replay import MockDevice, SimulatedClock, patched_time

clock = SimulatedClock.from_timestamp(1708600000.0)
device = MockDevice(fixture_dir="tests/fixtures/login_flow", clock=clock)

with patched_time(clock):
    result = my_tool.run(device)
    
assert device.is_manifest_exhausted()
```

## Validation During Replay

MockDevice enforces:
1. **Event ordering**: Screenshots and actions must occur in recorded order
2. **Target matching**: Click targets must match recorded target names
3. **Area bounds**: Click coordinates must be within recorded bounding boxes
4. **Swipe areas**: Swipe start/end points must be within recorded areas

Any deviation raises `ReplayDeviationError`.
