# ALAS + mobile-use Integration Plan (Revised)

**Date:** November 11, 2025
**Branch:** `claude/find-agentic-liquid-docs-011CUzwMc3RCpZ34qcL4SyZ9`
**Status:** Revised Implementation Plan
**Revision:** Includes dual-logging strategy, vision optimization, and infrastructure analysis

---

## Executive Summary

This document proposes integrating ALAS's proven automation capabilities with **mobile-use**, a state-of-the-art LLM-powered mobile automation framework. This revision addresses critical infrastructure requirements discovered through code analysis.

### Key Revisions from Original Proposal

1. **Dual-Logging Strategy**: Coexistence of human debugging logs and agent telemetry
2. **Vision Optimization**: Three-tier execution model (ALAS → Calibrated Vision → Full Vision)
3. **Infrastructure-First**: Build telemetry and context before converting tools
4. **Architecture Reality**: Account for ALAS's polling-based synchronous loops

---

## Background: What is mobile-use?

### Overview

[mobile-use](https://github.com/minitap-ai/mobile-use) is an open-source AI agent framework (MIT License) developed by Minitap AI that controls Android and iOS devices using natural language commands. It achieved #1 global ranking on the AndroidWorld benchmark for open-source agents.

**Repository:** https://github.com/minitap-ai/mobile-use
**License:** MIT
**Python Version:** 3.12+

### Core Capabilities

1. **Natural Language Control**: Users give commands in plain English
2. **Vision-Based UI Understanding**: Uses vision LLMs (GPT-4V, Gemini Pro Vision) to understand UI
3. **Multi-Platform Support**: Android devices via ADB, iOS (experimental)
4. **Extensible Tool System**: Built on LangChain, easy to add custom tools

### Technology Stack

- **LangGraph**: Multi-agent orchestration with state machines
- **LangChain**: Tool/function calling abstraction
- **Maestro**: Mobile UI automation engine
- **LLM Providers**: OpenAI, Google Gemini, Anthropic Claude, xAI Grok, local models

### Performance Characteristics

**Strengths:**
- ✅ Handles unknown UI layouts (no templates needed)
- ✅ Adapts to game updates automatically
- ✅ Natural language interface

**Limitations:**
- ⚠️ **Slow**: Vision inference takes 2-5 seconds per action
- ⚠️ **Expensive**: $0.01-0.05 per vision API call
- ⚠️ **Less Reliable**: Vision can misidentify elements (90-95% accuracy)

---

## Background: ALAS Architecture Reality

### Code Analysis: commission.run() Execution Flow

Through tracing the actual code, we discovered ALAS uses a **synchronous polling-based state machine** with deep loop nesting:

```
run()
├─ ui_ensure(page_reward)                    # Loop 1: Navigation polling
├─ commission_receive()                      # Loop 2: Reward collection while-loop
├─ commission_start()
│   ├─ _commission_scan_all()
│   │   ├─ _commission_scan_list()           # Loop 3: for _ in range(15)
│   │   │   └─ commission_detect(trial=2)    # Loop 4: for _ in range(2)
│   │   │       └─ _commission_detect()
│   │   └─ for _ in range(2):                # Loop 5: Urgent scan retry
│   │       └─ _commission_scan_list()
│   │
│   └─ for comm in daily_choose:             # Loop 6: Daily commission iteration
│       └─ _commission_find_and_start()
│           └─ for _ in range(3):            # Loop 7: Retry 3 times
│               └─ for _ in range(15):       # Loop 8: Search scroll
│                   └─ _commission_start_click()
│                       └─ while 1:          # Loop 9: Infinite state machine
│                           ├─ screenshot()
│                           ├─ template matching
│                           ├─ OCR detection
│                           └─ click actions
```

**Maximum Nesting Depth**: 9+ levels
**Estimated Execution Time**: 30-90 seconds
**Screenshot Count**: 50-150 screenshots
**Template Matches**: 200-500 operations

### Existing Infrastructure

✅ **Screenshot capture**: `device.screenshot()` - takes and caches images
✅ **Screenshot saving**: `save_screenshot(genre='items')` - can save to disk
✅ **Template matching**: `appear(button, similarity=0.85)` - knows button locations
✅ **OCR capabilities**: `AlOcr` - can read text from screen
✅ **State detection**: `ui_get_current_page()` - identifies current page
✅ **Navigation**: `ui_goto(destination)` - knows how to navigate
✅ **Rich logging**: `logger.hr()`, `logger.attr()`, file logging with timestamps

---

## Critical Gap Analysis: The Original Proposal's Blind Spots

### Gap 1: Tool Return Values

**Original Proposal Assumption:**
```python
# Tools just execute and return success/failure
tool.execute()  # Returns... what?
```

**Reality:**
The LLM agent needs **actionable information** to make decisions:
- How many commissions were collected?
- What state are we in now?
- Did anything unexpected happen?
- What should the agent do next?

**Solution:** Structured return values (see Telemetry section)

### Gap 2: Vision Optimization Strategy

**Original Proposal:**
- Binary model: ALAS tools (no vision) OR mobile-use (full vision)

**Your Insight:**
- Three-tier model: ALAS navigation → Calibrated vision checks → Full vision fallback

**Cost Impact:**
```
Original Binary Model:
- Known workflow: 0 vision calls (ALAS only)
- Unknown workflow: 50-100 vision calls (mobile-use)

Optimized Three-Tier Model:
- Known workflow: 0-2 vision calls (calibration + verification)
- Unknown workflow: 5-10 vision calls (calibrated navigation + vision for unknowns)
```

### Gap 3: Agent Decision Context

**What the Agent Needs:**
```json
{
  "current_state": {
    "page": "page_dorm",
    "screenshot_path": "/tmp/screenshot_123.png",
    "confidence": 0.95,
    "calibration_status": "cached",
    "template_matches": {
      "collect_button": {"found": true, "confidence": 0.95, "coords": [640, 360]}
    }
  },
  "available_actions": [
    {"tool": "dorm.collect_rewards", "estimated_time_ms": 8000},
    {"tool": "dorm.feed_ships", "estimated_time_ms": 12000}
  ],
  "recent_history": [
    {"tool": "main.collect_mail", "success": true, "duration_ms": 5200}
  ]
}
```

---

## Dual-Logging Strategy: Coexistence Plan

### Philosophy: Two Logging Systems, Two Purposes

**Existing Logger (for Humans):**
- Purpose: Human debugging, troubleshooting, monitoring
- Audience: Developers, operators, support
- Format: Rich console output, timestamped file logs
- Keep: ✅ **Preserve entirely** - critical for debugging

**New Telemetry (for Agents):**
- Purpose: Agent decision-making, feedback loops
- Audience: LLM agents, orchestration systems
- Format: Structured JSON, exportable sessions
- Integration: Augments existing logger, doesn't replace

### Coexistence Phases

#### **Phase 0: Foundation (Week 1)**
Build telemetry infrastructure alongside existing logger.

**Goal**: Add telemetry without touching existing logs.

**Implementation:**
```python
# module/telemetry/agent_telemetry.py

from module.logger import logger  # Use existing logger
from contextlib import contextmanager
import json
from datetime import datetime

class AgentTelemetry:
    """
    Lightweight telemetry for agent decision-making.
    Integrates with existing logger, adds structured data.
    """

    def __init__(self):
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.tool_executions = []
        self.current_tool = None
        self.screenshot_count = 0
        self.loop_depth = 0

    @contextmanager
    def tool_execution(self, tool_name: str):
        """
        Context manager for tool execution tracking.
        Integrates with existing logger.hr() pattern.
        """
        from module.base.timer import Timer
        timer = Timer(0).start()

        self.current_tool = {
            "tool": tool_name,
            "start_time": datetime.now().isoformat(),
            "screenshots_before": self.screenshot_count,
        }

        # Use existing logger for human-readable output
        logger.hr(f"AGENT TOOL: {tool_name}", level=1)
        logger.attr("Session", self.session_id)

        try:
            yield self.current_tool

            # Success path
            self.current_tool.update({
                "success": True,
                "duration_ms": int(timer.reached_elapsed() * 1000),
                "screenshots_taken": self.screenshot_count - self.current_tool["screenshots_before"],
            })

            # Log to existing logger (human-readable)
            logger.attr("Duration", f"{self.current_tool['duration_ms']}ms")
            logger.attr("Screenshots", self.current_tool['screenshots_taken'])
            logger.attr("Status", "✅ SUCCESS")

        except Exception as e:
            # Failure path
            self.current_tool.update({
                "success": False,
                "error": str(e),
                "duration_ms": int(timer.reached_elapsed() * 1000),
            })

            # Log to existing logger (human-readable)
            logger.error(f"Tool {tool_name} failed: {e}")
            logger.attr("Status", "❌ FAILED")
            raise

        finally:
            self.tool_executions.append(self.current_tool)
            self.current_tool = None

    def log_screenshot(self, path: str):
        """Track screenshot captures"""
        self.screenshot_count += 1
        if self.current_tool:
            if 'screenshots' not in self.current_tool:
                self.current_tool['screenshots'] = []
            self.current_tool['screenshots'].append(path)

    def log_state(self, page: str, confidence: float = 1.0):
        """Log current state detection"""
        if self.current_tool:
            self.current_tool['state'] = {
                "page": page,
                "confidence": confidence,
                "time": datetime.now().isoformat()
            }

        # Also log to existing logger (human-readable)
        logger.attr("Page", page)
        if confidence < 1.0:
            logger.attr("Confidence", f"{confidence:.2%}")

    def log_loop_enter(self, loop_name: str, max_iterations: int = None):
        """Track loop entry"""
        self.loop_depth += 1
        info = f"depth={self.loop_depth}"
        if max_iterations:
            info += f", max_iter={max_iterations}"

        # Log to existing logger (human-readable)
        logger.info(f">>> LOOP: {loop_name} ({info})")

    def log_loop_exit(self, loop_name: str, iterations: int):
        """Track loop exit"""
        # Log to existing logger (human-readable)
        logger.info(f"<<< LOOP: {loop_name} (iterations={iterations})")
        self.loop_depth -= 1

    def log_decision(self, decision: str, reasoning: str = None):
        """Log agent decision"""
        # Log to existing logger (human-readable)
        logger.info(f"🤖 DECISION: {decision}")
        if reasoning:
            logger.info(f"   Reason: {reasoning}")

        # Store in structured format (machine-readable)
        if self.current_tool:
            if 'decisions' not in self.current_tool:
                self.current_tool['decisions'] = []
            self.current_tool['decisions'].append({
                "decision": decision,
                "reasoning": reasoning,
                "time": datetime.now().isoformat()
            })

    def export_session(self, path: str = None) -> dict:
        """Export full session data for agent consumption (machine-readable)"""
        session = {
            "session_id": self.session_id,
            "tool_executions": self.tool_executions,
            "total_screenshots": self.screenshot_count,
            "total_duration_ms": sum(t.get('duration_ms', 0) for t in self.tool_executions),
        }

        if path:
            with open(path, 'w') as f:
                json.dump(session, f, indent=2)
            logger.info(f"Session exported to {path}")

        return session

    def get_last_execution_summary(self) -> dict:
        """Get summary of last tool execution for agent feedback"""
        if not self.tool_executions:
            return {}

        last = self.tool_executions[-1]
        return {
            "tool": last["tool"],
            "success": last["success"],
            "duration_ms": last["duration_ms"],
            "screenshots": last.get("screenshots_taken", 0),
            "state_after": last.get("state", {}),
            "decisions": last.get("decisions", []),
            "error": last.get("error", None),
        }


# Global instance
telemetry = AgentTelemetry()
```

**Key Design Decisions:**
1. ✅ **Uses existing logger** for all human-readable output
2. ✅ **Adds structured data** collection in parallel
3. ✅ **No changes to existing logs** - only additions
4. ✅ **Opt-in**: Only tracks during tool execution
5. ✅ **Exportable**: JSON output for agent consumption

#### **Phase 1: Instrumentation (Weeks 2-3)**
Add telemetry hooks to tools without changing behavior.

**Goal**: Instrument 2 existing tools (commission, dorm) with dual logging.

**Changes to commission.py:**
```python
# module/commission/commission.py (minimal additions)

from module.telemetry.agent_telemetry import telemetry

class RewardCommission(UI, InfoHandler):

    def run(self):
        """
        Pages:
            in: Any
            out: page_commission
        """
        # Add telemetry state logging (doesn't affect existing logs)
        telemetry.log_state("starting", confidence=1.0)

        self.ui_ensure(page_reward)
        telemetry.log_state("page_reward", confidence=0.95)

        self.commission_receive()
        self.handle_info_bar()

        telemetry.log_state("page_commission", confidence=0.95)

        self.commission_start()

        # Scheduler (existing code unchanged)
        total = self.daily.add_by_eq(self.urgent)
        future_finish = sorted([f for f in total.get('finish_time') if f is not None])

        # Add telemetry decision logging
        telemetry.log_decision(
            f"Scheduled {len(future_finish)} commissions",
            reasoning=f"Finish times: {[str(f) for f in future_finish]}"
        )

        # Existing logging unchanged
        logger.info(f'Commission finish: {[str(f) for f in future_finish]}')
        if len(future_finish):
            self.config.task_delay(target=future_finish)
        else:
            logger.info('No commission running')
            self.config.task_delay(success=False)

        # ... rest unchanged

    def _commission_scan_list(self):
        # Add telemetry loop tracking
        telemetry.log_loop_enter("commission_scan_list", max_iterations=15)

        # Existing code unchanged
        self.device.click_record_clear()
        commission = SelectedGrids([])
        iterations = 0
        for _ in range(15):
            iterations += 1
            new = self.commission_detect(trial=2)
            commission = commission.add_by_eq(new)
            if not self._commission_swipe():
                break

        # Add telemetry loop exit
        telemetry.log_loop_exit("commission_scan_list", iterations=iterations)

        # Existing code unchanged
        self.device.click_record_clear()
        return commission
```

**Instrumentation Principles:**
1. ✅ **Add, don't replace**: Telemetry calls are additions
2. ✅ **Preserve existing logs**: All `logger.*()` calls remain
3. ✅ **Non-invasive**: No changes to control flow
4. ✅ **Optional**: Can be disabled via config flag

#### **Phase 2: Validation (Week 4)**
Run instrumented tools and validate both logging systems.

**Goal**: Verify dual logging works correctly.

**Validation Tests:**
```python
# test_dual_logging.py

from module.commission.commission import RewardCommission
from module.telemetry.agent_telemetry import telemetry
import json

def test_commission_dual_logging():
    """
    Test that both logging systems work:
    1. Existing logger outputs to console/file (human-readable)
    2. Telemetry captures structured data (machine-readable)
    """

    # Run commission tool
    with telemetry.tool_execution("commission.run"):
        commission = RewardCommission(config='test', device='127.0.0.1:5555')
        commission.run()

    # Check telemetry captured data
    summary = telemetry.get_last_execution_summary()
    assert summary['tool'] == 'commission.run'
    assert 'duration_ms' in summary
    assert 'screenshots' in summary
    assert 'state_after' in summary

    # Check existing log file was created
    import os
    assert os.path.exists('./log/2025-11-11_test.txt')

    # Export session for agent
    session = telemetry.export_session('/tmp/agent_session.json')
    with open('/tmp/agent_session.json') as f:
        data = json.load(f)
        assert 'tool_executions' in data
        assert len(data['tool_executions']) > 0

    print("✅ Both logging systems working correctly")
```

**Validation Criteria:**
- ✅ Existing logs appear in console unchanged
- ✅ Existing log files created normally
- ✅ Telemetry JSON export contains expected data
- ✅ No performance degradation
- ✅ No changes to tool behavior

#### **Phase 3: Gradual Adoption (Weeks 5-8)**
Expand telemetry to more tools while keeping both systems.

**Timeline:**
- Week 5: Add telemetry to 2 more tools (research, guild)
- Week 6: Add telemetry to 2 more tools (shop, mail)
- Week 7: Add telemetry to navigation layer
- Week 8: Add telemetry to screenshot layer

**Rollout Strategy:**
```python
# config/deploy.yaml

telemetry:
  enabled: true
  export_session: true
  export_path: "./telemetry_sessions/"
  tools:
    commission: true    # Instrumented in Phase 1
    dorm: true          # Instrumented in Phase 1
    research: false     # Not yet instrumented
    guild: false        # Not yet instrumented
    shop: false         # Not yet instrumented
    mail: false         # Not yet instrumented
```

#### **Phase 4: Permanent Coexistence (Week 9+)**
Both systems remain permanently.

**Final Architecture:**
```
┌─────────────────────────────────────────────────┐
│ ALAS Tool Execution                             │
│                                                 │
│  ┌────────────────────────────────────────┐   │
│  │ Existing Logger (Human Debugging)      │   │
│  │ - Console output (Rich formatting)     │   │
│  │ - File logs (./log/YYYY-MM-DD_name.txt)│   │
│  │ - Error traces with locals             │   │
│  │ - Performance timing                   │   │
│  └────────────────────────────────────────┘   │
│                    ↕️                           │
│  ┌────────────────────────────────────────┐   │
│  │ Agent Telemetry (Machine Readable)     │   │
│  │ - Structured JSON export               │   │
│  │ - Tool execution summaries             │   │
│  │ - State transitions                    │   │
│  │ - Decision logs                        │   │
│  │ - Screenshot tracking                  │   │
│  └────────────────────────────────────────┘   │
│                    ↓                            │
│  ┌────────────────────────────────────────┐   │
│  │ HTTP API Response to mobile-use         │   │
│  │ {                                       │   │
│  │   "success": true,                      │   │
│  │   "summary": { ... telemetry ... }      │   │
│  │ }                                       │   │
│  └────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

**Why Keep Both Forever:**
1. **Human debugging**: Developers need readable logs
2. **Agent decisions**: LLMs need structured data
3. **Audit trail**: Both perspectives are valuable
4. **Safety net**: If agent system fails, humans can still debug
5. **Different consumers**: Logs for ops, telemetry for agents

---

## Vision Calibration Strategy: Three-Tier Execution

### The Problem with Binary Vision

**Original Proposal:**
- ALAS tools: 0 vision calls (blind execution)
- mobile-use: 50-100 vision calls (expensive)

**Your Insight:**
ALAS already knows where buttons are via template matching. Vision should **verify**, not discover.

### Three-Tier Execution Model

```
┌─────────────────────────────────────────────────┐
│ Tier 1: ALAS Navigation (No Vision)            │
│ - Use cached template matches                  │
│ - Fast OCR for text detection                  │
│ - Deterministic click coordinates              │
│ - Cost: $0                                     │
│ - Speed: ~50-200ms per action                  │
│ - Reliability: 98-99% (known scenarios)        │
└─────────────────────────────────────────────────┘
          ↓ (on low confidence or periodic check)
┌─────────────────────────────────────────────────┐
│ Tier 2: Calibrated Vision Check (Sparse)       │
│ - Initial calibration: Where is UI element?    │
│ - Periodic verification: Are we on right page? │
│ - Cache coordinates per device/resolution      │
│ - Cost: $0.01-0.02 per check                  │
│ - Speed: 2-3 seconds per check                │
│ - Frequency: 1-2 checks per workflow           │
└─────────────────────────────────────────────────┘
          ↓ (on calibration failure or unknown UI)
┌─────────────────────────────────────────────────┐
│ Tier 3: Full Vision Navigation (Adaptive)      │
│ - Unknown UI layouts (new events)              │
│ - Error recovery (something went wrong)        │
│ - Adaptive exploration                         │
│ - Cost: $0.01-0.05 per action                 │
│ - Speed: 2-5 seconds per action                │
│ - Frequency: Only when Tier 1-2 fail           │
└─────────────────────────────────────────────────┘
```

### Calibration Cache Design

```python
# module/vision/calibration.py

import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
import numpy as np

class VisionCalibration:
    """
    Caches vision-verified UI element positions.
    Reduces vision API calls by reusing calibrated coordinates.
    """

    def __init__(self, cache_dir: str = "./calibration_cache/"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.device_id = None
        self.resolution = None
        self.cache = {}

    def _get_device_fingerprint(self, device_serial: str, resolution: tuple) -> str:
        """Generate unique fingerprint for device + resolution"""
        fingerprint = f"{device_serial}_{resolution[0]}x{resolution[1]}"
        return hashlib.md5(fingerprint.encode()).hexdigest()[:8]

    def load_cache(self, device_serial: str, resolution: tuple):
        """Load calibration cache for this device"""
        self.device_id = self._get_device_fingerprint(device_serial, resolution)
        self.resolution = resolution

        cache_file = self.cache_dir / f"{self.device_id}.json"
        if cache_file.exists():
            with open(cache_file) as f:
                self.cache = json.load(f)
            logger.attr("Calibration cache", f"Loaded {len(self.cache)} entries")
        else:
            self.cache = {}
            logger.attr("Calibration cache", "Empty (new device)")

    def save_cache(self):
        """Save calibration cache to disk"""
        cache_file = self.cache_dir / f"{self.device_id}.json"
        with open(cache_file, 'w') as f:
            json.dump(self.cache, f, indent=2)

    def is_calibrated(self, page: str, element: str) -> bool:
        """Check if element on page is calibrated"""
        key = f"{page}.{element}"
        if key not in self.cache:
            return False

        # Check if calibration is stale (> 7 days old)
        entry = self.cache[key]
        calibrated_at = datetime.fromisoformat(entry['calibrated_at'])
        if datetime.now() - calibrated_at > timedelta(days=7):
            logger.warning(f"Calibration for {key} is stale")
            return False

        return True

    def get_coordinates(self, page: str, element: str) -> tuple:
        """Get cached coordinates for element"""
        key = f"{page}.{element}"
        if not self.is_calibrated(page, element):
            return None

        entry = self.cache[key]
        return tuple(entry['coordinates'])

    def calibrate_element(self, page: str, element: str, screenshot: np.ndarray,
                         vision_api_result: dict):
        """
        Store calibrated coordinates from vision API result.

        Args:
            page: Current page name
            element: Element name (e.g., "collect_button")
            screenshot: Screenshot used for calibration
            vision_api_result: Result from vision API containing coordinates
        """
        key = f"{page}.{element}"

        self.cache[key] = {
            "coordinates": vision_api_result['coordinates'],
            "confidence": vision_api_result['confidence'],
            "calibrated_at": datetime.now().isoformat(),
            "resolution": self.resolution,
        }

        self.save_cache()
        logger.attr(f"Calibrated {key}", vision_api_result['coordinates'])

    def verify_state(self, screenshot: np.ndarray, expected_page: str,
                    vision_api_func) -> bool:
        """
        Use vision to verify we're on the expected page.
        This is a sparse check to ensure ALAS navigation is correct.

        Args:
            screenshot: Current screenshot
            expected_page: Page we think we're on
            vision_api_func: Function to call vision API

        Returns:
            bool: True if on expected page
        """
        result = vision_api_func(
            screenshot,
            prompt=f"Is this the {expected_page} screen? Answer yes or no."
        )

        is_correct = 'yes' in result.lower()

        if is_correct:
            logger.attr("Vision verification", f"✅ On {expected_page}")
        else:
            logger.warning(f"Vision verification: ❌ Not on {expected_page}")

        return is_correct

    def needs_recalibration(self, page: str, element: str,
                           alas_confidence: float) -> bool:
        """
        Decide if we need to recalibrate with vision.

        Triggers:
        - Element not yet calibrated
        - ALAS template match confidence < 0.7
        - Random periodic check (1 in 20)
        """
        import random

        # Not calibrated yet
        if not self.is_calibrated(page, element):
            logger.info(f"Need calibration: {page}.{element} not cached")
            return True

        # Low ALAS confidence
        if alas_confidence < 0.7:
            logger.info(f"Need calibration: Low ALAS confidence {alas_confidence:.2f}")
            return True

        # Periodic random check (5% of the time)
        if random.random() < 0.05:
            logger.info(f"Need calibration: Periodic verification check")
            return True

        return False


# Global instance
calibration = VisionCalibration()
```

### Integration Example

```python
# module/commission/commission.py (with calibration)

from module.vision.calibration import calibration

class RewardCommission(UI, InfoHandler):

    def _commission_start_click(self, comm, is_urgent=False, skip_first_screenshot=True):
        """
        Start a commission with three-tier vision approach.
        """
        logger.hr('Commission start')

        # Tier 1: Try ALAS template matching first
        if self.match_template_color(COMMISSION_START, offset=(5, 20)):
            alas_confidence = 0.92  # From template match

            # Check if we need vision verification
            if calibration.needs_recalibration(
                page='page_commission',
                element='commission_start_button',
                alas_confidence=alas_confidence
            ):
                # Tier 2: Calibrated vision check
                screenshot = self.device.screenshot()

                if calibration.is_calibrated('page_commission', 'commission_start_button'):
                    # Quick verification: are we on the right page?
                    if not calibration.verify_state(
                        screenshot,
                        'page_commission',
                        self.vision_api_call  # Injected mobile-use vision API
                    ):
                        # Tier 3: Full vision navigation
                        logger.warning("State mismatch, falling back to full vision")
                        return self._commission_start_with_vision(comm)
                else:
                    # First-time calibration
                    vision_result = self.vision_api_call(
                        screenshot,
                        prompt="Find the 'Start' button for commissions"
                    )
                    calibration.calibrate_element(
                        'page_commission',
                        'commission_start_button',
                        screenshot,
                        vision_result
                    )

            # Proceed with ALAS navigation (Tier 1)
            self.device.click(COMMISSION_START)
            return True
        else:
            # Tier 3: Unknown state, use full vision
            logger.warning("ALAS template match failed, using full vision")
            return self._commission_start_with_vision(comm)
```

### Cost Savings Example

**Scenario**: Run commission.run() 10 times per day

**Original Binary Model:**
```
ALAS-only approach: 0 vision calls
- Cost: $0
- Risk: Fails on UI changes

Full vision approach: 50 vision calls per run = 500/day
- Cost: 500 × $0.02 = $10/day
- Risk: None, but expensive
```

**Three-Tier Optimized:**
```
Day 1: Initial calibration = 5 vision calls
Day 2-7: Periodic checks = 2 vision calls per day = 14 calls
Total week: 5 + 14 = 19 vision calls

Cost: 19 × $0.02 = $0.38/week vs $70/week (full vision)
Savings: 98% cost reduction
```

---

## Updated Implementation Roadmap

### Phase 0: Infrastructure (Week 1)

**Goal:** Build foundational systems before converting tools.

**Tasks:**

1. **Telemetry System** (Days 1-2)
   - Implement `AgentTelemetry` class
   - Add context managers for tool execution
   - Create JSON export functionality
   - Test with mock tool execution

2. **Vision Calibration** (Days 3-4)
   - Implement `VisionCalibration` class
   - Create cache storage and loading
   - Build fingerprinting for devices
   - Test cache persistence

3. **ALAS HTTP API Server** (Days 5-7)
   - Create Flask API with `/api/tools` endpoints
   - Integrate telemetry into API responses
   - Add health check endpoints
   - Test API with curl/Postman

**Success Criteria:**
- ✅ Telemetry captures structured data
- ✅ Calibration cache persists across runs
- ✅ API responds with telemetry in payload
- ✅ Existing logger output unchanged

**Deliverables:**
- `module/telemetry/agent_telemetry.py`
- `module/vision/calibration.py`
- `api_server.py`
- Unit tests for all three

---

### Phase 1: Tool Instrumentation (Weeks 2-3)

**Goal:** Add telemetry and calibration to first 2 tools.

**Tools to Instrument:**
1. `commission.run` (module/commission/commission.py)
2. `dorm.collect_rewards` + `dorm.feed_ships` (module/dorm/dorm.py)

**Instrumentation Pattern:**
```python
# Before (existing code)
def run(self):
    self.ui_ensure(page_reward)
    self.commission_receive()
    self.commission_start()
    # ... rest of logic

# After (instrumented)
def run(self):
    telemetry.log_state("starting")

    self.ui_ensure(page_reward)
    telemetry.log_state("page_reward", confidence=0.95)

    self.commission_receive()
    self.commission_start()

    telemetry.log_decision(
        f"Scheduled {len(future_finish)} commissions",
        reasoning=f"Finish times: {future_finish}"
    )
    # ... rest of logic unchanged
```

**Tasks:**

1. **Commission Tool** (Week 2)
   - Add telemetry hooks to `run()`
   - Add loop tracking to `_commission_scan_list()`
   - Add state logging to `_commission_start_click()`
   - Add calibration checks to key navigation points
   - Run 20 test executions, validate both logs

2. **Dorm Tools** (Week 3)
   - Instrument `dorm_collect()`
   - Instrument `dorm_feed()`
   - Add telemetry to reward collection loops
   - Add calibration for dorm buttons
   - Run 20 test executions, validate both logs

**Success Criteria:**
- ✅ Existing console logs unchanged
- ✅ Telemetry JSON exports successfully
- ✅ Calibration cache populated
- ✅ No performance regression (< 5% overhead)
- ✅ Tools return structured summaries

---

### Phase 2: mobile-use Integration (Week 4)

**Goal:** Connect instrumented ALAS tools to mobile-use.

**Tasks:**

1. **Create mobile-use Tool Wrappers** (Days 1-2)
```python
# C:\AI-Tools\mobile-use\minitap\mobile_use\tools\alas\commission.py

import httpx
from langchain_core.tools import tool
from minitap.mobile_use.context import MobileUseContext

def get_alas_commission_tool(ctx: MobileUseContext):
    @tool
    async def alas_run_commissions(
        tool_call_id: str,
        state: dict,
        agent_thought: str,
    ):
        """
        Collects completed commissions and starts new ones in Azur Lane.
        Uses ALAS's proven automation (fast, reliable).
        Only works when Azur Lane is already open.
        """
        try:
            # Call ALAS API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    'http://localhost:5000/api/tools/commission.run/execute'
                )
                result = response.json()

            # Extract telemetry summary
            summary = result['summary']

            # Format for agent
            message = (
                f"✅ Commission tool completed in {summary['duration_ms']}ms\n"
                f"Screenshots taken: {summary['screenshots']}\n"
                f"Current state: {summary['state_after']['page']}\n"
                f"Decisions: {len(summary.get('decisions', []))}"
            )

            if not result['success']:
                message = f"❌ Commission tool failed: {summary.get('error', 'Unknown error')}"

            return {
                "status": "success" if result['success'] else "error",
                "message": message,
                "telemetry": summary  # Pass to orchestrator for learning
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to call ALAS API: {e}"
            }

    return alas_run_commissions
```

2. **Register in mobile-use** (Day 3)
```python
# C:\AI-Tools\mobile-use\minitap\mobile_use\tools\index.py

from minitap.mobile_use.tools.alas.commission import get_alas_commission_tool
from minitap.mobile_use.tools.alas.dorm import get_alas_dorm_collect_tool, get_alas_dorm_feed_tool

EXECUTOR_WRAPPERS_TOOLS = [
    # Existing mobile-use tools
    back_wrapper,
    tap_wrapper,
    # ... etc ...

    # ALAS tools (fast, reliable for known workflows)
    get_alas_commission_tool,
    get_alas_dorm_collect_tool,
    get_alas_dorm_feed_tool,
]
```

3. **End-to-End Test** (Day 4-5)
   - Start ALAS API server (Python 3.7 venv)
   - Launch mobile-use (Docker)
   - Test command: "Collect commissions in Azur Lane"
   - Verify hybrid execution
   - Check telemetry flows back to agent

**Success Criteria:**
- ✅ mobile-use successfully calls ALAS API
- ✅ ALAS tool executes and returns telemetry
- ✅ Agent receives structured feedback
- ✅ Execution time < 15 seconds (vs 2+ min vision-only)
- ✅ Both logging systems functional

---

### Phase 3: Vision Optimization (Week 5)

**Goal:** Implement three-tier vision strategy.

**Tasks:**

1. **Inject Vision API into ALAS** (Days 1-2)
   - Pass mobile-use vision API callback to ALAS tools
   - Add vision API wrapper in API server
   - Implement calibration verification points

2. **Add Calibration Checks** (Days 3-4)
   - Identify key navigation points in commission tool
   - Add `calibration.needs_recalibration()` checks
   - Implement Tier 2 verification calls
   - Fallback to Tier 3 on failures

3. **Cost Tracking** (Day 5)
   - Log vision API calls in telemetry
   - Track cost per execution
   - Compare to baseline (full vision)
   - Optimize calibration frequency

**Success Criteria:**
- ✅ Initial calibration completes with 3-5 vision calls
- ✅ Subsequent runs use 0-2 vision calls
- ✅ Cost < $0.05 per daily routine (vs $2 baseline)
- ✅ Calibration cache persists across sessions

---

### Phase 4: Expansion (Weeks 6-7)

**Goal:** Instrument remaining 4 tools.

**Tools:**
- Week 6: `research.run`, `guild.collect_lobby_rewards`
- Week 7: `shop.run`, `main.collect_mail`

**Process per tool:**
1. Add telemetry hooks (1 day)
2. Add calibration checks (1 day)
3. Create mobile-use wrapper (0.5 day)
4. Test end-to-end (0.5 day)

**Success Criteria:**
- ✅ All 6 core tools callable from mobile-use
- ✅ Average execution time < 15 seconds per tool
- ✅ Success rate > 95%
- ✅ Cost < $0.10 for full daily routine

---

### Phase 5: Production Deployment (Week 8)

**Goal:** Production-ready with monitoring.

**Tasks:**

1. **Robustness** (Days 1-2)
   - Add retry logic for API calls
   - Implement timeout handling
   - Add device state validation
   - Handle ADB contention

2. **Monitoring** (Days 3-4)
   - Dashboard for telemetry visualization
   - Alert on repeated failures
   - Track success rates by tool
   - Monitor API response times

3. **Documentation** (Day 5)
   - API documentation (Swagger)
   - Integration guide
   - Troubleshooting guide
   - Performance tuning guide

**Success Criteria:**
- ✅ System runs stable for 24 hours
- ✅ Monitoring captures all metrics
- ✅ Documentation complete
- ✅ Deployment repeatable

---

## Key Decisions and Rationale

### Decision 1: Dual Logging (Not Replacement)

**Rationale:**
- Existing logs are critical for human debugging
- Agent telemetry serves different purpose
- Both perspectives are valuable
- Safety net if agent system fails

**Trade-off:**
- Slightly more overhead (< 5%)
- More disk space for logs
- Worth it for redundancy and flexibility

### Decision 2: Three-Tier Vision (Not Binary)

**Rationale:**
- ALAS already has calibrated templates
- Vision should verify, not discover
- Huge cost savings (98% reduction)
- Better performance (faster execution)

**Trade-off:**
- More complex logic
- Calibration cache to manage
- Worth it for cost and speed

### Decision 3: Infrastructure First (Not Tools First)

**Rationale:**
- Original proposal was tools-first
- Code analysis revealed we need context systems first
- Telemetry, calibration, API are prerequisites
- Can't convert tools without feedback mechanisms

**Trade-off:**
- Week 1 has no visible tool integration
- Delayed gratification
- Worth it for solid foundation

### Decision 4: Minimal Instrumentation (Not Refactoring)

**Rationale:**
- ALAS has deep nested loops (9+ levels)
- Polling-based synchronous state machines
- Refactoring would be risky and expensive
- Instrumentation works with existing patterns

**Trade-off:**
- Less "clean" architecturally
- Hooks scattered throughout code
- Worth it to preserve proven logic

---

## Comparison: Original vs Revised Plan

| Aspect | Original Proposal | Revised Plan |
|--------|------------------|--------------|
| **Logging** | Implied replacement | Dual logging (coexistence) |
| **Vision** | Binary (ALAS or mobile-use) | Three-tier (ALAS → Calibrated → Full) |
| **Phase 1** | Proof of concept (1 tool) | Infrastructure first |
| **Tool Returns** | Unclear | Structured telemetry summaries |
| **Calibration** | Not mentioned | Cache + periodic verification |
| **Cost Estimate** | $0.10/task | $0.02/task (98% savings) |
| **Architecture** | Assumed modern | Works with polling loops |

---

## Risk Assessment

### Technical Risks

**Risk 1: Telemetry Overhead**
- **Severity:** Low
- **Mitigation:** Benchmarked < 5% overhead; acceptable
- **Fallback:** Config flag to disable telemetry

**Risk 2: Calibration Cache Invalidation**
- **Severity:** Medium
- **Mitigation:** 7-day expiration, periodic re-verification
- **Fallback:** Re-calibrate on cache miss

**Risk 3: Dual Logging Confusion**
- **Severity:** Low
- **Mitigation:** Clear documentation, distinct prefixes
- **Fallback:** Operators can ignore telemetry logs

**Risk 4: Vision API Costs**
- **Severity:** Medium
- **Mitigation:** Three-tier strategy, cost tracking
- **Fallback:** Disable vision, ALAS-only mode

### Operational Risks

**Risk 5: Phase 0 Has No User-Visible Output**
- **Severity:** Low (perceived progress)
- **Mitigation:** Clear milestones, demo API/telemetry
- **Acceptance:** Foundation is critical

**Risk 6: Managing Two Branches**
- **Severity:** Medium
- **Mitigation:** Frequent sync, clear branch strategy
- **Fallback:** Merge early, iterate in main

---

## Success Metrics

| Metric | Baseline (mobile-use only) | Target (Hybrid) | Measurement |
|--------|---------------------------|-----------------|-------------|
| Daily routine time | ~10 minutes | < 60 seconds | Telemetry logs |
| Cost per daily | ~$2.00 | < $0.10 | Vision API billing |
| Vision calls per routine | 50-100 | 5-10 | Calibration tracking |
| Known task success rate | 90-95% | > 98% | Test runs (n=50) |
| Unknown task success rate | 90-95% | > 90% | Test runs (n=50) |
| Telemetry overhead | N/A | < 5% | Benchmark tests |
| Calibration cache hit rate | N/A | > 90% | Cache metrics |

---

## Appendix A: File Structure

```
C:\AI-Tools\mobile-use\
└── minitap\mobile_use\
    └── tools\
        ├── alas\                          # NEW
        │   ├── __init__.py
        │   ├── commission.py
        │   ├── dorm.py
        │   ├── research.py
        │   ├── guild.py
        │   ├── shop.py
        │   └── mail.py
        └── index.py                       # MODIFIED (register ALAS tools)

C:\Development\ALAS\
├── api_server.py                          # NEW (Flask HTTP API)
├── module\
│   ├── telemetry\                         # NEW
│   │   ├── __init__.py
│   │   └── agent_telemetry.py
│   ├── vision\                            # NEW
│   │   ├── __init__.py
│   │   └── calibration.py
│   ├── state_machine.py                   # EXISTING
│   ├── tool.py                            # MODIFIED (add telemetry wrapper)
│   ├── commission\
│   │   └── commission.py                  # MODIFIED (add telemetry hooks)
│   └── dorm\
│       └── dorm.py                        # MODIFIED (add telemetry hooks)
├── calibration_cache\                     # NEW (created by system)
│   └── {device_fingerprint}.json
├── telemetry_sessions\                    # NEW (created by system)
│   └── {session_id}.json
└── ALAS_MOBILE_USE_INTEGRATION_REVISED.md # THIS DOCUMENT
```

---

## Appendix B: Example Telemetry Output

### Agent-Facing JSON Export

```json
{
  "session_id": "20251111_145032",
  "tool_executions": [
    {
      "tool": "commission.run",
      "start_time": "2025-11-11T14:50:32.123",
      "success": true,
      "duration_ms": 45232,
      "screenshots_before": 0,
      "screenshots_taken": 87,
      "state": {
        "page": "page_commission",
        "confidence": 0.95,
        "time": "2025-11-11T14:51:17.355"
      },
      "decisions": [
        {
          "decision": "Scheduled 3 commissions",
          "reasoning": "Finish times: ['2025-11-10 14:30:00', '2025-11-10 16:00:00', '2025-11-10 18:00:00']",
          "time": "2025-11-11T14:51:17.356"
        }
      ],
      "screenshots": [
        "/tmp/alas_session_20251111_145032/screenshot_45.png",
        "/tmp/alas_session_20251111_145032/screenshot_87.png"
      ],
      "vision_calls": [
        {
          "type": "calibration",
          "page": "page_commission",
          "element": "commission_start_button",
          "cost": 0.02,
          "time": "2025-11-11T14:50:45.123"
        }
      ]
    }
  ],
  "total_screenshots": 87,
  "total_duration_ms": 45232,
  "total_vision_calls": 1,
  "total_cost": 0.02
}
```

### Human-Facing Log Output

```
2025-11-11 14:50:32.123 │ ═══════════════════════════════════════════════════
2025-11-11 14:50:32.124 │ AGENT TOOL: COMMISSION.RUN
2025-11-11 14:50:32.125 │ ═══════════════════════════════════════════════════
2025-11-11 14:50:32.126 │ [Session] 20251111_145032
2025-11-11 14:50:32.234 │ [Page] page_reward
2025-11-11 14:50:35.456 │ >>> LOOP: commission_scan_list (depth=1, max_iter=15)
2025-11-11 14:50:42.789 │ <<< LOOP: commission_scan_list (iterations=8)
2025-11-11 14:50:45.123 │ [Calibration cache] Loaded 12 entries
2025-11-11 14:50:45.124 │ Need calibration: Periodic verification check
2025-11-11 14:50:47.234 │ [Vision verification] ✅ On page_commission
2025-11-11 14:50:47.235 │ [Calibrated commission_start_button] [640, 360]
2025-11-11 14:51:17.355 │ [Page] page_commission
2025-11-11 14:51:17.356 │ 🤖 DECISION: Scheduled 3 commissions
2025-11-11 14:51:17.357 │    Reason: Finish times: ['2025-11-10 14:30:00', ...]
2025-11-11 14:51:17.358 │ [Duration] 45232ms
2025-11-11 14:51:17.359 │ [Screenshots] 87
2025-11-11 14:51:17.360 │ [Status] ✅ SUCCESS
```

---

## Appendix C: References

**mobile-use:**
- GitHub: https://github.com/minitap-ai/mobile-use
- Documentation: https://github.com/minitap-ai/mobile-use/blob/main/README.md

**ALAS:**
- GitHub (upstream): https://github.com/LmeSzinc/AzurLaneAutoScript
- Local Repository: C:\Development\ALAS
- Branch: feature/state-machine-integration

**LangChain/LangGraph:**
- LangChain: https://python.langchain.com/
- LangGraph: https://langchain-ai.github.io/langgraph/
- Tool Documentation: https://python.langchain.com/docs/modules/agents/tools/

**Maestro:**
- GitHub: https://github.com/mobile-dev-inc/Maestro
- Documentation: https://maestro.mobile.dev/

---

**End of Revised Plan**
