# ALAS MCP Server Smoke Test Report

**Test Date:** 2026-03-02 21:20:06 (local time)  
**Test Environment:** Windows 11  
**Emulator:** MEmuPlayer  
**Serial:** 127.0.0.1:21513  

---

## Test Summary

| Test Category | Status | Details |
|--------------|--------|---------|
| Emulator Running | ✅ PASS | MEmuPlayer processes confirmed running |
| ADB Connectivity | ✅ PASS | Connected to 127.0.0.1:21513 |
| ADB Screenshot | ⚠️ PARTIAL | Captures 2KB PNG but images are pure black |
| State Machine | ❌ FAIL | Cannot determine current page (black screens) |
| Tool Discovery | ✅ PASS | 10 tools discovered |
| MCP Server Startup | ✅ PASS | Server initializes correctly |

**Overall Result:** 4/5 tests passed (1 partial, 1 failed)

---

## Detailed Test Results

### 1. Emulator Status Check
**Result:** ✅ PASS

```
MEmuConsole.exe     36192 Console    1     59,752 K
MEmuSVC.exe          3892 Console    1     21,364 K
MEmu.exe            39724 Console    1    131,692 K
MEmuHyper.exe       38880 Console    1    369,516 K
```

All MEmuPlayer processes are active and running.

---

### 2. ADB Connectivity
**Result:** ✅ PASS

- **ADB Server:** Running on 127.0.0.1:5037
- **Device Serial:** 127.0.0.1:21513 (auto-detected)
- **Connection Status:** Successfully connected
- **Package Name:** com.YoStarEN.AzurLane
- **Screen Size:** 1280x720

**Note:** Configuration shows serial 127.0.0.1:21513. The AGENTS.md documentation mentions 127.0.0.1:21503, but the actual configured and working serial is 127.0.0.1:21513.

---

### 3. ADB Screenshot Test
**Result:** ⚠️ PARTIAL

- **Screenshot Captured:** Yes (2KB PNG)
- **Screenshot Quality:** Pure black images detected
- **Warning Messages:**
  ```
  WARNING: Received pure black screenshots from emulator, color: (0.0, 0.0, 0.0)
  WARNING: Uninstall minicap and retry
  ```

**Impact:** Screenshots are being captured but show only black pixels. This prevents visual recognition and state detection.

**Possible Causes:**
1. Emulator screen is off or minimized
2. MEmuPlayer screenshot method incompatibility
3. Display driver issues
4. Emulator needs to be in foreground

**Resolution Attempts by ALAS:**
- Automatically removed minicap and retried
- Switched to uiautomator2 screenshot method
- MaaTouch control method initialized successfully

---

### 4. State Machine Query
**Result:** ❌ FAIL

- **Error:** `GamePageUnknownError`
- **Cause:** Cannot recognize game page from pure black screenshots
- **Attempted Recognition:** 25+ "Unknown ui page" messages before timeout

**Supported Pages (from log):**
- `page_main`, `page_campaign_menu`, `page_campaign`, `page_fleet`
- `page_main_white`, `page_unknown`, `page_exercise`, `page_daily`
- `page_event`, `page_sp`, `page_coalition`, `page_os`, `page_archives`
- `page_reward`, `page_mission`, `page_guild`, `page_commission`
- `page_tactical`, `page_battle_pass`, `page_event_list`, `page_raid`
- `page_dock`, `page_research`, `page_shipyard`, `page_meta`
- `page_storage`, `page_reshmenu`, `page_dormmenu`, `page_dorm`
- `page_meowfficer`, `page_academy`, `page_private_quarters`
- `page_game_room`, `page_shop`, `page_munitions`, `page_supply_pack`
- `page_build`, `page_mail`, `page_channel`, `page_rpg_stage`
- `page_rpg_story`, `page_rpg_city`, `page_hospital`

**Recommendation:** Ensure the game is visible on the emulator screen and the emulator window is not minimized.

---

### 5. Tool Discovery
**Result:** ✅ PASS

**Discovered Tools (10 total):**
1. `main.collect_mail`
2. `workflow.daily_base_sweep`
3. `dorm.collect_rewards`
4. `dorm.feed_ships`
5. `dorm.buy_furniture`
6. `dorm.dorm_menu`
7. `reward.receive_all`
8. `commission.run`
9. `tactical.run`
10. `research.run`

All MCP tools are properly registered and discoverable.

---

### 6. MCP Server Startup
**Result:** ✅ PASS

- **ALASContext Initialization:** Success
- **Config Name:** alas
- **Device:** 127.0.0.1:21513
- **Control Method:** MaaTouch
- **Screenshot Method:** uiautomator2 (fallback from minicap)

Server initialized successfully with proper imports and configuration loading.

---

## Issues Found

### Issue 1: Pure Black Screenshots (CRITICAL)
**Severity:** High  
**Impact:** Prevents visual state recognition and automation

**Symptoms:**
- Screenshots return pure black (RGB: 0.0, 0.0, 0.0)
- State machine cannot identify current page
- All visual recognition fails

**Troubleshooting Steps:**
1. Ensure MEmuPlayer window is visible and not minimized
2. Check if the Azur Lane game is actually running
3. Try restarting the emulator
4. Check MEmuPlayer display settings
5. Verify GPU acceleration is enabled

### Issue 2: Documentation Outdated
**Severity:** Low  
**File:** AGENTS.md

The AGENTS.md file mentions serial `127.0.0.1:21503`, but the actual configured serial is `127.0.0.1:21513`. This should be updated to match the actual configuration.

---

## Recommendations

### Immediate Actions
1. **Fix Screenshot Issue:** Ensure MEmuPlayer is running with visible display
2. **Update Documentation:** Correct serial number in AGENTS.md
3. **Test Game Visibility:** Verify Azur Lane is running in the emulator

### Verification Steps
1. Open MEmuPlayer and ensure Azur Lane is visible
2. Re-run smoke test: `cd agent_orchestrator && uv run python smoke_test_live.py`
3. Verify screenshots show game content instead of black images
4. Check state machine can identify the current page

### Long-term Improvements
1. Add screenshot validation to smoke test
2. Implement better error messages for black screen conditions
3. Add automatic recovery for screenshot failures

---

## Test Commands Used

```bash
# Run smoke test
cd agent_orchestrator && uv run python smoke_test_live.py

# Check emulator processes
tasklist | findstr MEmu

# Check ALAS configuration
grep -r "Emulator.*Serial" alas_wrapped/config/
```

---

## Conclusion

The MCP server and ADB connectivity are functional, but **visual recognition is blocked by pure black screenshots**. This is likely an emulator display issue rather than an MCP server problem.

**Next Step:** Ensure MEmuPlayer is displaying the Azur Lane game properly before re-running the smoke test.
