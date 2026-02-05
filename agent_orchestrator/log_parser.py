#!/usr/bin/env python3
"""
ALAS Log Parser - Parse and summarize AzurLaneAutoScript bot logs

Zero-dependency CLI tool that analyzes ALAS logs and produces actionable summaries.
Supports multiple output modes: summary, timeline, errors, combat stats, and more.
"""

import re
import sys
import argparse
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Iterator, TextIO, Any
from collections import defaultdict, Counter
from enum import Enum


# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class LogLine:
    """Represents a single parsed log line"""
    line_number: int
    timestamp: Optional[datetime] = None
    level: Optional[str] = None
    message: str = ""
    raw: str = ""
    is_separator: bool = False
    separator_title: Optional[str] = None
    continuation_lines: List[str] = field(default_factory=list)

    def full_message(self) -> str:
        """Get complete message including continuation lines"""
        if not self.continuation_lines:
            return self.message
        return self.message + "\n" + "\n".join(self.continuation_lines)

@dataclass
class SessionState:
    """
    Shared state context passed between analyzers (The "Event Bus").
    
    Why this exists:
    Previously, analyzers (Error, Combat, Task) were isolated.
    The CombatAnalyzer didn't know if a crash occurred in ErrorAnalyzer.
    This shared state allows ErrorAnalyzer to signal "CRASHED" and CombatAnalyzer to read it.
    """
    current_task: Optional[str] = None
    in_combat: bool = False
    last_crash_error: Optional[str] = None
    last_timestamp: Optional[datetime] = None


# ============================================================================
# Log Parser
# ============================================================================

class LogParser:
    """Parses ALAS log files into structured LogLine objects"""

    # Pattern: 2026-01-25 12:00:59.205 | INFO | Message
    LOG_PATTERN = re.compile(
        r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})\s*\|\s*(\w+)\s*\|\s*(.*)$'
    )

    # Separator line patterns
    SEPARATOR_PATTERN = re.compile(r'^[═─]{50,}$')
    TITLE_PATTERN = re.compile(r'^[═─\s]+([A-Z\s]+?)[═─\s]*$')

    @classmethod
    def parse(cls, lines: Iterator[str]) -> Iterator[LogLine]:
        """Parse log lines into structured LogLine objects"""
        line_num = 0
        current_log: Optional[LogLine] = None

        for raw_line in lines:
            line_num += 1
            line = raw_line.rstrip('\n\r')

            # Check for separator lines
            if cls.SEPARATOR_PATTERN.match(line):
                if current_log:
                    yield current_log
                    current_log = None

                # Check next line for title
                title = None
                title_match = cls.TITLE_PATTERN.match(line)
                if title_match:
                    title = title_match.group(1).strip()

                yield LogLine(
                    line_number=line_num,
                    raw=line,
                    is_separator=True,
                    separator_title=title,
                    message=title or ""
                )
                continue

            # Try to parse as log line
            match = cls.LOG_PATTERN.match(line)

            if match:
                # Yield previous log if exists
                if current_log:
                    yield current_log

                # Parse new log line
                timestamp_str, level, message = match.groups()
                timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')

                current_log = LogLine(
                    line_number=line_num,
                    timestamp=timestamp,
                    level=level,
                    message=message.strip(),
                    raw=line
                )
            else:
                # Continuation line
                if current_log and line.strip():
                    current_log.continuation_lines.append(line)
                elif line.strip():
                    # Orphan line (no parent log entry)
                    if current_log:
                        yield current_log
                    current_log = LogLine(
                        line_number=line_num,
                        message=line.strip(),
                        raw=line
                    )

        # Yield final log
        if current_log:
            yield current_log


# ============================================================================
# Analyzers
# ============================================================================

class BaseAnalyzer:
    """Base class for all analyzers"""
    def feed(self, log: LogLine, state: SessionState):
        pass
    
    def finalize(self, state: SessionState):
        pass

@dataclass
class TaskRun:
    """Represents a single task execution"""
    name: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    success: bool = True
    error_type: Optional[str] = None
    line_start: int = 0
    line_end: int = 0

    @property
    def duration(self) -> Optional[timedelta]:
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None


class TaskAnalyzer(BaseAnalyzer):
    """Tracks task lifecycle and execution"""

    def __init__(self):
        self.tasks: List[TaskRun] = []
        self.current_task: Optional[TaskRun] = None
        self.task_counts: Counter = Counter()

    def feed(self, log: LogLine, state: SessionState):
        """Process a log line for task information"""
        if not log.message:
            return

        msg = log.message

        # Task start: "Scheduler: Start task `TaskName`"
        if "Scheduler: Start task" in msg:
            match = re.search(r"Start task `([^`]+)`", msg)
            if match:
                task_name = match.group(1)
                
                # Update shared state
                state.current_task = task_name

                # End previous task if exists
                if self.current_task:
                    self.current_task.end_time = log.timestamp
                    self.current_task.line_end = log.line_number

                # Start new task
                self.current_task = TaskRun(
                    name=task_name,
                    start_time=log.timestamp,
                    line_start=log.line_number
                )
                self.tasks.append(self.current_task)
                self.task_counts[task_name] += 1

        # Section headers (alternative task markers)
        elif log.is_separator and log.separator_title:
            title = log.separator_title
            if title and title not in ['START', 'DEVICE']:
                # This might be a task section
                if self.current_task and not self.current_task.start_time:
                    self.current_task.start_time = log.timestamp

        # Task delay/skip
        elif "Delay task" in msg or "Skip task" in msg:
            if self.current_task:
                self.current_task.end_time = log.timestamp
                self.current_task.line_end = log.line_number
                self.current_task = None
                state.current_task = None

        # Error in current task
        elif log.level in ['ERROR', 'CRITICAL'] and self.current_task:
            self.current_task.success = False
            # Try to extract exception type
            exc_match = re.search(r'(\w+Error|\w+Exception):', msg)
            if exc_match:
                self.current_task.error_type = exc_match.group(1)

    def finalize(self, state: SessionState):
        """Called when parsing is complete"""
        if self.current_task and state.last_timestamp:
            self.current_task.end_time = state.last_timestamp


class ErrorAnalyzer(BaseAnalyzer):
    """Tracks errors, warnings, and exceptions"""

    def __init__(self):
        self.errors: List[LogLine] = []
        self.warnings: List[LogLine] = []
        self.criticals: List[LogLine] = []
        self.exception_counts: Counter = Counter()
        self.error_saves: List[str] = []

    def feed(self, log: LogLine, state: SessionState):
        """Process a log line for errors"""
        msg = log.full_message()

        # Detect crashes (Tracebacks or Function calls in INFO)
        is_traceback = "Traceback (most recent call last):" in msg or "Function calls:" in msg
        
        if log.level == 'ERROR':
            self.errors.append(log)
            self._extract_exception(log, state)
        elif log.level == 'WARNING':
            self.warnings.append(log)
        elif log.level == 'CRITICAL':
            self.criticals.append(log)
            self._extract_exception(log, state)
        elif is_traceback and log.level == 'INFO':
            # OPINIONATED CHANGE: Treat INFO-level tracebacks as exceptions.
            # Why: ALAS often logs "GameStuckError" or stack traces as INFO to avoid
            # polluting the console with red text. Without this, the parser thinks
            # the bot is fine when it's actually stuck in a retry loop.
            self._extract_exception(log, state)

        # Detect error saves
        if "Saving error:" in log.message:
            match = re.search(r'Saving error:\s*(.+)', log.message)
            if match:
                self.error_saves.append(match.group(1))

    def _extract_exception(self, log: LogLine, state: SessionState):
        """Extract exception type from log message"""
        msg = log.full_message()

        # Pattern: ExceptionName: message
        match = re.search(r'(\w+(?:Error|Exception)):', msg)
        if match:
            exc_name = match.group(1)
            self.exception_counts[exc_name] += 1
            
            # Update shared state
            state.last_crash_error = exc_name


class CombatAnalyzer(BaseAnalyzer):
    """Tracks combat statistics, especially exercise fights"""

    @dataclass
    class Fight:
        opponent: Optional[int] = None
        try_num: Optional[int] = None
        hp_start: Optional[int] = None
        hp_end: Optional[int] = None
        timestamp: Optional[datetime] = None
        won: Optional[bool] = None
        crashed: bool = False  # New field for crash detection

    def __init__(self):
        self.fights: List[CombatAnalyzer.Fight] = []
        self.current_fight: Optional[CombatAnalyzer.Fight] = None

    def feed(self, log: LogLine, state: SessionState):
        """Process a log line for combat information"""
        msg = log.message

        # <<< OPPONENT: N >>>
        if match := re.search(r'OPPONENT:\s*(\d+)', msg):
            # Close previous fight if needed (assume success if not crashed?)
            # Actually, usually a fight ends with a result or a new opponent.
            if self.current_fight:
                self.fights.append(self.current_fight)
            
            self.current_fight = self.Fight(
                opponent=int(match.group(1)),
                timestamp=log.timestamp
            )
            state.in_combat = True
            state.last_crash_error = None # Reset crash for new fight

        # <<< TRY: N >>>
        elif match := re.search(r'TRY:\s*(\d+)', msg):
            if self.current_fight:
                self.current_fight.try_num = int(match.group(1))

        # HP flow: [XX% - YY%]
        elif match := re.search(r'\[(\d+)%\s*-\s*(\d+)%\]', msg):
            if self.current_fight:
                self.current_fight.hp_start = int(match.group(1))
                self.current_fight.hp_end = int(match.group(2))
                # Determine win/loss (HP went down = win usually)
                self.current_fight.won = int(match.group(2)) < int(match.group(1))
        
        # Check for crash in combat
        if state.in_combat and state.last_crash_error:
            if self.current_fight:
                self.current_fight.crashed = True
                self.current_fight.won = False # Explicitly not a win
                # We don't close the fight yet, just mark it. 
                # It will be closed by next opponent or finalize.

        # <<< COMBAT END >>>
        # OPINIONATED CHANGE: Explicitly close combat state on this signal.
        # Why: Prevents "Zombie Fights". If the bot crashes 5 minutes AFTER a fight
        # (while idling), we don't want to blame the previous successful fight.
        # We must strictly quarantine the "in_combat" state to the actual battle duration.
        if "<<< COMBAT END >>>" in msg:
            state.in_combat = False
            state.last_crash_error = None

    def finalize(self, state: SessionState):
        """Called when parsing is complete"""
        if self.current_fight:
            self.fights.append(self.current_fight)


class AkashiAnalyzer(BaseAnalyzer):
    """Tracks Operation Siren merchant (Akashi) events"""

    def __init__(self):
        self.discoveries: List[LogLine] = []
        self.purchases: List[str] = []
        self.mismatch_warnings: Counter = Counter()
        self.max_mismatch_sim: Dict[str, float] = {}

    def feed(self, log: LogLine, state: SessionState):
        msg = log.message
        
        # Discovery: "Found Akashi on (X, Y)"
        if "Found Akashi" in msg:
            self.discoveries.append(log)
            
        # Purchase: "Bought item: ItemName"
        elif "Bought item:" in msg:
            match = re.search(r"Bought item:\s*(.+)\.", msg)
            if match:
                self.purchases.append(match.group(1))

        # Mismatch Warning: "Channel mismatch fixed in TEMPLATE_NAME. Sim: 0.XXX"
        elif "Channel mismatch fixed in" in msg:
            match = re.search(r"Channel mismatch fixed in ([\w_]+)\. Sim: ([\d.]+)", msg)
            if match:
                template_name = match.group(1)
                sim = float(match.group(2))
                self.mismatch_warnings[template_name] += 1
                if sim > self.max_mismatch_sim.get(template_name, 0):
                    self.max_mismatch_sim[template_name] = sim


class ResourceAnalyzer(BaseAnalyzer):
    """Tracks resource readings from OCR"""

    @dataclass
    class Reading:
        resource: str
        value: int
        timestamp: Optional[datetime] = None

    def __init__(self):
        self.readings: List[ResourceAnalyzer.Reading] = []

    def feed(self, log: LogLine, state: SessionState):
        """Process a log line for resource information"""
        msg = log.message

        # [OCR_*] patterns
        if match := re.search(r'\[OCR_(\w+)\]\s*(\d+)', msg):
            self.readings.append(self.Reading(
                resource=match.group(1),
                value=int(match.group(2)),
                timestamp=log.timestamp
            ))

        # Exercise remain
        elif match := re.search(r'exercise.*remain.*?(\d+)', msg, re.IGNORECASE):
            self.readings.append(self.Reading(
                resource='EXERCISE_REMAIN',
                value=int(match.group(1)),
                timestamp=log.timestamp
            ))


class NavigationAnalyzer(BaseAnalyzer):
    """Tracks page navigation and UI interactions"""

    def __init__(self):
        self.page_switches: List[Dict] = []
        self.click_count: int = 0
        self.unknown_pages: int = 0

    def feed(self, log: LogLine, state: SessionState):
        """Process a log line for navigation information"""
        msg = log.message

        # Page switch: page_x -> page_y
        if match := re.search(r'Page switch:\s*(\S+)\s*->\s*(\S+)', msg):
            self.page_switches.append({
                'from': match.group(1),
                'to': match.group(2),
                'timestamp': log.timestamp
            })

        # Click events
        elif re.search(r'Click\s*\(', msg):
            self.click_count += 1

        # Unknown pages
        elif 'Unknown ui page' in msg:
            self.unknown_pages += 1


class LootAnalyzer(BaseAnalyzer):
    """Tracks acquired items (Ships, Gear, Resources)"""
    
    def __init__(self):
        self.items: Counter = Counter()
        self.recent_loot: List[str] = []

    def feed(self, log: LogLine, state: SessionState):
        msg = log.message
        # Patterns: 
        # "Get 2x Gold Plate"
        # "Acquire Ship: Enterprise"
        # (Regex needs to be fuzzy as ALAS logging varies)
        if msg.startswith("Get ") or msg.startswith("Acquire ") or msg.startswith("Obtain "):
            self.items[msg] += 1
            self.recent_loot.append(msg)


class SkipAnalyzer(BaseAnalyzer):
    """Tracks why tasks were skipped"""
    
    def __init__(self):
        self.reasons: Counter = Counter()

    def feed(self, log: LogLine, state: SessionState):
        msg = log.message
        # Skip task Commission (Reason: No available commission)
        if "Skip task" in msg:
            if match := re.search(r'Skip task .* \((Reason: .+?)\)', msg):
                reason = match.group(1)
                self.reasons[reason] += 1
            else:
                self.reasons["Unspecified"] += 1


class DeviceAnalyzer(BaseAnalyzer):
    """Tracks device/ADB connection issues"""

    def __init__(self):
        self.adb_timeouts: int = 0
        self.connection_errors: List[LogLine] = []
        self.maatouch_events: List[Dict] = []

    def feed(self, log: LogLine, state: SessionState):
        """Process a log line for device information"""
        msg = log.message

        if 'AdbTimeout' in msg or 'adb timeout' in msg.lower():
            self.adb_timeouts += 1

        if 'MaaTouch' in msg:
            self.maatouch_events.append({
                'message': msg,
                'timestamp': log.timestamp
            })

        if log.level in ['ERROR', 'WARNING'] and any(
            kw in msg.lower() for kw in ['connection', 'device', 'adb']
        ):
            self.connection_errors.append(log)


# ============================================================================
# Analyzer Pipeline
# ============================================================================

class AnalyzerPipeline:
    """Coordinates multiple analyzers"""

    def __init__(self):
        self.task = TaskAnalyzer()
        self.error = ErrorAnalyzer()
        self.combat = CombatAnalyzer()
        self.resource = ResourceAnalyzer()
        self.navigation = NavigationAnalyzer()
        self.device = DeviceAnalyzer()
        self.loot = LootAnalyzer()
        self.skip = SkipAnalyzer()
        self.akashi = AkashiAnalyzer()
        
        self.state = SessionState()
        self.options: Dict[str, bool] = {} # Feature flags

        # Session metadata
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.total_lines: int = 0

    def feed(self, log: LogLine):
        """Feed a log line to all analyzers"""
        self.total_lines += 1

        # Track session time
        if log.timestamp:
            if not self.start_time:
                self.start_time = log.timestamp
            self.end_time = log.timestamp
            self.state.last_timestamp = log.timestamp

        # Feed to all analyzers
        self.error.feed(log, self.state)
        self.task.feed(log, self.state)
        self.combat.feed(log, self.state)
        self.resource.feed(log, self.state)
        self.navigation.feed(log, self.state)
        self.device.feed(log, self.state)
        self.akashi.feed(log, self.state)
        
        # Feed optional analyzers
        self.loot.feed(log, self.state)
        self.skip.feed(log, self.state)

    def finalize(self):
        """Called when parsing is complete"""
        self.task.finalize(self.state)
        self.combat.finalize(self.state)


# ============================================================================
# Colors (ANSI)
# ============================================================================

class Colors:
    """ANSI color codes"""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'

    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    CYAN = '\033[36m'

    BOLD_RED = '\033[1;31m'

    enabled = True

    @classmethod
    def disable(cls):
        """Disable all colors"""
        cls.enabled = False
        cls.RESET = cls.BOLD = cls.DIM = ''
        cls.RED = cls.GREEN = cls.YELLOW = cls.BLUE = cls.CYAN = ''
        cls.BOLD_RED = ''

    @classmethod
    def c(cls, text: str, color: str) -> str:
        """Colorize text if colors enabled"""
        if not cls.enabled:
            return text
        return f"{color}{text}{cls.RESET}"

    @classmethod
    def safe_char(cls, unicode_char: str, ascii_fallback: str) -> str:
        """Return unicode char or ASCII fallback based on environment"""
        # Use ASCII on Windows console or if colors disabled
        if not cls.enabled or sys.platform == 'win32':
            return ascii_fallback
        return unicode_char


# ============================================================================
# Formatters
# ============================================================================

class SummaryFormatter:
    """Produces compact single-screen overview"""

    @staticmethod
    def format(pipeline: AnalyzerPipeline) -> str:
        c = Colors.c
        lines = []

        # Header
        sep = "=" * 60
        lines.append(c(sep, Colors.BOLD))
        lines.append(c("ALAS LOG SUMMARY", Colors.BOLD))
        lines.append(c(sep, Colors.BOLD))
        lines.append("")

        # Session info
        if pipeline.start_time and pipeline.end_time:
            duration = pipeline.end_time - pipeline.start_time
            lines.append(f"Session: {pipeline.start_time.strftime('%Y-%m-%d %H:%M:%S')} to "
                        f"{pipeline.end_time.strftime('%H:%M:%S')}")
            lines.append(f"Duration: {c(str(duration).split('.')[0], Colors.GREEN)}")
        lines.append(f"Total lines: {c(str(pipeline.total_lines), Colors.CYAN)}")
        lines.append("")

        # Task summary
        lines.append(c("Tasks", Colors.BOLD))
        lines.append(c("-" * 60, Colors.DIM))
        if pipeline.task.tasks:
            for task_name, count in pipeline.task.task_counts.most_common():
                # Calculate avg duration
                task_runs = [t for t in pipeline.task.tasks if t.name == task_name]
                durations = [t.duration for t in task_runs if t.duration]
                avg_dur = sum(durations, timedelta()) / len(durations) if durations else None

                failed = sum(1 for t in task_runs if not t.success)
                status = c(f"({failed} failed)", Colors.RED) if failed else c("[OK]", Colors.GREEN)

                dur_str = f"avg {str(avg_dur).split('.')[0]}" if avg_dur else "incomplete"
                lines.append(f"  {c(task_name, Colors.CYAN):30} x{count:2} {status:15} {dur_str}")
        else:
            lines.append(c("  No tasks found", Colors.DIM))
        lines.append("")

        # Skip Reasons (Hidden by default)
        if pipeline.options.get('reasons') and pipeline.skip.reasons:
            lines.append(c("Skip Reasons", Colors.BOLD))
            lines.append(c("-" * 60, Colors.DIM))
            for reason, count in pipeline.skip.reasons.most_common():
                 lines.append(f"  {c(reason, Colors.YELLOW):40} x{count}")
            lines.append("")

        # Loot (Hidden by default)
        if pipeline.options.get('loot') and pipeline.loot.items:
            lines.append(c("Loot Acquired", Colors.BOLD))
            lines.append(c("-" * 60, Colors.DIM))
            for item, count in pipeline.loot.items.most_common(20):
                 lines.append(f"  {item:40} x{count}")
            if len(pipeline.loot.items) > 20:
                lines.append(c(f"  ... and {len(pipeline.loot.items) - 20} more", Colors.DIM))
            lines.append("")

        # Error summary
        lines.append(c("Errors & Warnings", Colors.BOLD))
        lines.append(c("-" * 60, Colors.DIM))
        lines.append(f"  Critical: {c(str(len(pipeline.error.criticals)), Colors.BOLD_RED)}")
        lines.append(f"  Errors:   {c(str(len(pipeline.error.errors)), Colors.RED)}")
        lines.append(f"  Warnings: {c(str(len(pipeline.error.warnings)), Colors.YELLOW)}")

        if pipeline.error.exception_counts:
            lines.append(f"\n  Exception types:")
            for exc_type, count in pipeline.error.exception_counts.most_common(5):
                lines.append(f"    {c(exc_type, Colors.RED):30} x{count}")
        lines.append("")

        # Combat summary
        if pipeline.combat.fights:
            lines.append(c("Combat (Exercise)", Colors.BOLD))
            lines.append(c("-" * 60, Colors.DIM))
            wins = sum(1 for f in pipeline.combat.fights if f.won)
            losses = sum(1 for f in pipeline.combat.fights if f.won is False)
            crashes = sum(1 for f in pipeline.combat.fights if f.crashed)
            
            lines.append(f"  Fights: {len(pipeline.combat.fights)}")
            lines.append(f"  Wins:   {c(str(wins), Colors.GREEN)}")
            lines.append(f"  Losses: {c(str(losses), Colors.RED)}")
            if crashes > 0:
                lines.append(f"  Crashes:{c(str(crashes), Colors.BOLD_RED)}")
                
            if wins + losses > 0:
                winrate = wins / (wins + losses) * 100
                lines.append(f"  Winrate: {c(f'{winrate:.1f}%', Colors.CYAN)}")
            lines.append("")

        # Akashi summary
        if pipeline.akashi.discoveries or pipeline.akashi.purchases or pipeline.akashi.mismatch_warnings:
            lines.append(c("Akashi (Merchant)", Colors.BOLD))
            lines.append(c("-" * 60, Colors.DIM))
            lines.append(f"  Discoveries: {c(str(len(pipeline.akashi.discoveries)), Colors.GREEN)}")
            lines.append(f"  Purchases:   {c(str(len(pipeline.akashi.purchases)), Colors.CYAN)}")
            
            if pipeline.akashi.mismatch_warnings:
                lines.append(c("\n  Recognition Noise (Channel Mismatches):", Colors.YELLOW))
                for template, count in pipeline.akashi.mismatch_warnings.most_common(5):
                    max_sim = pipeline.akashi.max_mismatch_sim.get(template, 0)
                    lines.append(f"    {template:30} x{count:4} (max sim: {max_sim:.3f})")
            lines.append("")

        # Device issues
        if pipeline.device.adb_timeouts or pipeline.device.connection_errors:
            lines.append(c("Device Issues", Colors.BOLD))
            lines.append(c("-" * 60, Colors.DIM))
            lines.append(f"  ADB timeouts: {c(str(pipeline.device.adb_timeouts), Colors.YELLOW)}")
            lines.append(f"  Connection errors: {c(str(len(pipeline.device.connection_errors)), Colors.YELLOW)}")
            lines.append("")

        return "\n".join(lines)


class TimelineFormatter:
    """Produces chronological task list"""

    @staticmethod
    def format(pipeline: AnalyzerPipeline) -> str:
        c = Colors.c
        lines = []

        lines.append(c("TASK TIMELINE", Colors.BOLD))
        lines.append(c("-" * 80, Colors.DIM))
        lines.append("")

        for task in pipeline.task.tasks:
            start = task.start_time.strftime('%H:%M:%S') if task.start_time else '??:??:??'
            end = task.end_time.strftime('%H:%M:%S') if task.end_time else 'ongoing'
            dur = str(task.duration).split('.')[0] if task.duration else '???'

            status = c("[OK]", Colors.GREEN) if task.success else c("[FAIL]", Colors.RED)
            name = c(task.name, Colors.CYAN)

            line = f"{c(start, Colors.DIM)} -> {end:8} [{dur:>8}] {status} {name}"
            if not task.success and task.error_type:
                line += c(f" ({task.error_type})", Colors.RED)
            lines.append(line)

        return "\n".join(lines)


class ErrorFormatter:
    """Produces error-focused view"""

    @staticmethod
    def format(pipeline: AnalyzerPipeline) -> str:
        c = Colors.c
        lines = []
        show_trace = pipeline.options.get('trace', False)

        lines.append(c("ERRORS & WARNINGS", Colors.BOLD))
        lines.append(c("-" * 80, Colors.DIM))
        lines.append("")

        def format_log(log: LogLine) -> str:
            time_str = log.timestamp.strftime('%H:%M:%S') if log.timestamp else '???'
            msg = log.full_message() if show_trace else log.message
            return f"  {c(time_str, Colors.DIM)} | {msg}"

        # Criticals
        if pipeline.error.criticals:
            lines.append(c("CRITICAL", Colors.BOLD_RED))
            for log in pipeline.error.criticals[:10]:  # Limit output
                lines.append(format_log(log))
            lines.append("")

        # Errors
        if pipeline.error.errors:
            lines.append(c("ERRORS", Colors.RED))
            for log in pipeline.error.errors[:20]:  # Limit output
                lines.append(format_log(log))
            lines.append("")

        # Warnings
        if pipeline.error.warnings:
            lines.append(c("WARNINGS", Colors.YELLOW))
            for log in pipeline.error.warnings[:20]:  # Limit output
                lines.append(format_log(log))
            lines.append("")

        # Exception summary
        if pipeline.error.exception_counts:
            lines.append(c("Exception Summary", Colors.BOLD))
            for exc_type, count in pipeline.error.exception_counts.most_common():
                lines.append(f"  {c(exc_type, Colors.RED):40} x{count}")
            lines.append("")

        # Error saves
        if pipeline.error.error_saves:
            lines.append(c("Error Saves", Colors.BOLD))
            for save_path in pipeline.error.error_saves:
                lines.append(f"  {save_path}")
            lines.append("")

        return "\n".join(lines)


class CombatFormatter:
    """Produces combat statistics"""

    @staticmethod
    def format(pipeline: AnalyzerPipeline) -> str:
        c = Colors.c
        lines = []

        lines.append(c("COMBAT STATISTICS", Colors.BOLD))
        lines.append(c("-" * 80, Colors.DIM))
        lines.append("")

        if not pipeline.combat.fights:
            lines.append(c("No combat data found", Colors.DIM))
            return "\n".join(lines)

        for fight in pipeline.combat.fights:
            time_str = fight.timestamp.strftime('%H:%M:%S') if fight.timestamp else '???'
            opp = f"Opponent {fight.opponent}" if fight.opponent else "Unknown"
            try_str = f"Try {fight.try_num}" if fight.try_num else ""

            result = ""
            if fight.crashed:
                result = c("CRASH", Colors.BOLD_RED)
            elif fight.won is True:
                result = c("WIN", Colors.GREEN)
            elif fight.won is False:
                result = c("LOSS", Colors.RED)

            hp_str = ""
            if fight.hp_start is not None and fight.hp_end is not None:
                hp_str = f"[{fight.hp_start}% -> {fight.hp_end}%]"

            lines.append(f"{c(time_str, Colors.DIM)} | {opp:15} {try_str:10} {result:10} {hp_str}")

        lines.append("")
        wins = sum(1 for f in pipeline.combat.fights if f.won)
        losses = sum(1 for f in pipeline.combat.fights if f.won is False)
        crashes = sum(1 for f in pipeline.combat.fights if f.crashed)
        
        lines.append(f"Total: {len(pipeline.combat.fights)} fights | "
                    f"Wins: {c(str(wins), Colors.GREEN)} | "
                    f"Losses: {c(str(losses), Colors.RED)} | "
                    f"Crashes: {c(str(crashes), Colors.BOLD_RED)}")

        return "\n".join(lines)


class ResourceFormatter:
    """Produces resource tracking view"""

    @staticmethod
    def format(pipeline: AnalyzerPipeline) -> str:
        c = Colors.c
        lines = []

        lines.append(c("RESOURCE TRACKING", Colors.BOLD))
        lines.append(c("-" * 80, Colors.DIM))
        lines.append("")

        if not pipeline.resource.readings:
            lines.append(c("No resource data found", Colors.DIM))
            return "\n".join(lines)

        # Group by resource type
        by_type = defaultdict(list)
        for reading in pipeline.resource.readings:
            by_type[reading.resource].append(reading)

        for resource, readings in sorted(by_type.items()):
            lines.append(c(resource, Colors.CYAN))
            for reading in readings[:10]:  # Limit
                time_str = reading.timestamp.strftime('%H:%M:%S') if reading.timestamp else '???'
                lines.append(f"  {c(time_str, Colors.DIM)} | {reading.value}")
            lines.append("")

        return "\n".join(lines)


class JsonFormatter:
    """Produces JSON output"""

    @staticmethod
    def format(pipeline: AnalyzerPipeline) -> str:
        data = {
            'session': {
                'start_time': pipeline.start_time.isoformat() if pipeline.start_time else None,
                'end_time': pipeline.end_time.isoformat() if pipeline.end_time else None,
                'total_lines': pipeline.total_lines
            },
            'tasks': [
                {
                    'name': t.name,
                    'start_time': t.start_time.isoformat() if t.start_time else None,
                    'end_time': t.end_time.isoformat() if t.end_time else None,
                    'duration_seconds': t.duration.total_seconds() if t.duration else None,
                    'success': t.success,
                    'error_type': t.error_type
                }
                for t in pipeline.task.tasks
            ],
            'errors': {
                'critical_count': len(pipeline.error.criticals),
                'error_count': len(pipeline.error.errors),
                'warning_count': len(pipeline.error.warnings),
                'exception_types': dict(pipeline.error.exception_counts)
            },
            'combat': {
                'total_fights': len(pipeline.combat.fights),
                'wins': sum(1 for f in pipeline.combat.fights if f.won),
                'losses': sum(1 for f in pipeline.combat.fights if f.won is False),
                'crashes': sum(1 for f in pipeline.combat.fights if f.crashed)
            },
            'device': {
                'adb_timeouts': pipeline.device.adb_timeouts,
                'connection_errors': len(pipeline.device.connection_errors)
            }
        }
        return json.dumps(data, indent=2)


# ============================================================================
# File Discovery
# ============================================================================

def find_latest_log() -> Optional[Path]:
    """Find the latest ALAS log file"""
    script_dir = Path(__file__).parent
    log_dir = script_dir.parent / 'Alas-with-Dashboard' / 'log'

    if not log_dir.exists():
        return None

    # Find all alas_*.txt files
    log_files = list(log_dir.glob('*_alas.txt'))

    if not log_files:
        return None

    # Return most recent by modification time
    return max(log_files, key=lambda p: p.stat().st_mtime)


def tail_file(file_path: Path, n: int) -> Iterator[str]:
    """Read last N lines from file efficiently"""
    with open(file_path, 'rb') as f:
        # Seek to end
        f.seek(0, 2)
        file_size = f.tell()

        # Estimate bytes to read (assume ~100 chars per line)
        bytes_to_read = min(n * 150, file_size)
        f.seek(max(0, file_size - bytes_to_read))

        # Read and decode
        lines = f.read().decode('utf-8', errors='replace').splitlines()

        # Return last N lines
        for line in lines[-n:]:
            yield line + '\n'


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Parse and summarize ALAS bot logs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python log_parser.py --latest --summary
  python log_parser.py ./log/*.txt --daily
  python log_parser.py --latest --trace --errors
  cat log.txt | python log_parser.py --loot
        """
    )

    # Input sources
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument('--latest', '-l', action='store_true',
                            help='Auto-find latest alas log')
    
    # Allow both positional args and --file for compatibility
    parser.add_argument('files', nargs='*', type=Path,
                            help='Log files to parse (supports wildcards in shell)')
    parser.add_argument('--file', '-f', type=Path,
                            help='Specific log file (legacy)')

    # Output modes
    parser.add_argument('--summary', '-s', action='store_true',
                       help='One-screen overview (default)')
    parser.add_argument('--timeline', '-t', action='store_true',
                       help='Chronological task list')
    parser.add_argument('--errors', '-e', action='store_true',
                       help='Errors and warnings only')
    parser.add_argument('--combat', '-c', action='store_true',
                       help='Combat statistics')
    parser.add_argument('--resources', '-r', action='store_true',
                       help='Resource tracking')
    parser.add_argument('--json', '-j', action='store_true',
                       help='JSON output')

    # Granular Drill-down Flags (Phase 2)
    parser.add_argument('--trace', action='store_true',
                       help='Show full Python stack traces for errors')
    parser.add_argument('--loot', action='store_true',
                       help='Show acquired items (Drops/Loot)')
    parser.add_argument('--reasons', action='store_true',
                       help='Show reasons why tasks were skipped')
    parser.add_argument('--daily', action='store_true',
                       help='Group stats by day/file (Multi-file mode)')

    # Options
    parser.add_argument('--tail', '-n', type=int, metavar='N',
                       help='Only parse last N lines (Single file only)')
    parser.add_argument('--no-color', action='store_true',
                       help='Disable ANSI colors')

    args = parser.parse_args()

    # Disable colors if requested
    if args.no_color:
        Colors.disable()

    # Resolve input files
    files_to_read = []
    
    if args.latest:
        latest = find_latest_log()
        if not latest:
            print("Error: Could not find latest log file", file=sys.stderr)
            sys.exit(1)
        files_to_read.append(latest)
    else:
        # Support both positional files and --file arg
        if args.files:
            files_to_read.extend(args.files)
        if args.file:
            files_to_read.append(args.file)
        
        # Deduplicate while preserving order
        files_to_read = list(dict.fromkeys(files_to_read))
    
    # Validation
    if args.tail and len(files_to_read) > 1:
        print("Error: --tail only supports single file input", file=sys.stderr)
        sys.exit(1)

    # Initialize Pipeline
    pipeline = AnalyzerPipeline()
    
    # Configure Pipeline Options
    pipeline.options = {
        'trace': args.trace,
        'loot': args.loot,
        'reasons': args.reasons
    }

    # Processing Loop
    if not files_to_read:
        # Stdin mode
        if args.tail:
             # Buffer stdin for tail
            all_lines = list(sys.stdin)
            lines = iter(all_lines[-args.tail:])
        else:
            lines = sys.stdin
        
        for log in LogParser.parse(lines):
            pipeline.feed(log)
            
    else:
        # File mode
        print(f"Parsing {len(files_to_read)} file(s)...", file=sys.stderr)
        for fpath in files_to_read:
            # print(f"Reading: {fpath}", file=sys.stderr) # Optional verbose
            if args.tail:
                lines = tail_file(fpath, args.tail)
            else:
                lines = open(fpath, 'r', encoding='utf-8', errors='replace')
            
            for log in LogParser.parse(lines):
                pipeline.feed(log)
            
            if not args.tail:
                lines.close()

    pipeline.finalize()

    # Determine output modes (default to summary)
    modes = []
    if args.summary or not any([args.timeline, args.errors, args.combat, args.resources, args.json]):
        modes.append(('summary', SummaryFormatter))
    if args.timeline:
        modes.append(('timeline', TimelineFormatter))
    if args.errors:
        modes.append(('errors', ErrorFormatter))
    if args.combat:
        modes.append(('combat', CombatFormatter))
    if args.resources:
        modes.append(('resources', ResourceFormatter))
    if args.json:
        modes.append(('json', JsonFormatter))

    # Output
    for i, (name, formatter) in enumerate(modes):
        if i > 0:
            print("\n\n")
        print(formatter.format(pipeline))


if __name__ == '__main__':
    main()
