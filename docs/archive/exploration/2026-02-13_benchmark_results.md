# ALAS Benchmark Results (MEmu, EN)

> **Date**: 2026-02-13  
> **Time Window**: 21:44:58 - 21:45:46  
> **Log Source**: `alas_wrapped/log/2026-02-13_PatrickCustom.txt`

## Environment Snapshot

- Emulator: `MEmu`
- Serial: `127.0.0.1:21503`
- ADB binary: `C:\Program Files\Microvirt\MEmu\adb.exe`
- Package: `com.YoStarEN.AzurLane`
- Device orientation: `0 (Normal)`
- Resolution: `1280x720`

## Startup Behavior Before Benchmark

- During warm-up, repeated warnings appeared:
  - `Received pure black screenshots from emulator`
  - `Screenshot method 'ADB' may not work...`
  - `Unknown ui page`
- The bot then recovered to `page_main`, navigated to campaign pages, and completed benchmark execution.

## Methodology Caveat (Important)

- This run used the built-in benchmark flow that primarily scored methods by latency.
- In this environment, black-frame behavior was observed in runtime logs, which means throughput alone is not a sufficient health signal.
- Practical rule: methods that produce black frames should be treated as failed/unreliable, even when their measured time is low.

## Screenshot Benchmark Results

| Method | Time | Speed |
|---|---:|---|
| ADB | 0.128s | Very Fast |
| ADB_nc | 0.392s | Medium |
| uiautomator2 | 0.128s | Very Fast |
| aScreenCap | 0.097s | Ultra Fast |
| aScreenCap_nc | 0.108s | Very Fast |
| DroidCast | 0.071s | Ultra Fast |
| DroidCast_raw | 0.311s | Medium |

**Raw benchmark recommendation (speed-only)**: `DroidCast (0.071s)`  
**Operational recommendation for this environment**: treat `DroidCast` as unreliable when black-frame behavior is present; prefer stable fallback methods (`aScreenCap` / `aScreenCap_nc`, then `uiautomator2`).

## Control Benchmark Results

| Method | Time | Speed |
|---|---:|---|
| ADB | 0.127s | Medium |
| uiautomator2 | 0.143s | Medium |
| minitouch | 0.056s | Fast |
| MaaTouch | 0.059s | Fast |

**ALAS recommendation**: `MaaTouch` (ALAS preference when minitouch and MaaTouch are both top candidates)

## Conclusions

1. `DroidCast` had the fastest measured latency, but speed-only ranking is not trustworthy when black frames occur.
2. `MaaTouch` remained the recommended control path.
3. `aScreenCap`/`aScreenCap_nc` performed well and are viable stable fallback screenshot methods.
4. `ADB_nc` and `DroidCast_raw` were materially slower than top options.
5. The key issue from this session is reliability: black-frame behavior can invalidate a "fastest method" recommendation.
