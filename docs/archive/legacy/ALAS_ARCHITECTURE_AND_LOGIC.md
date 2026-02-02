# ALAS Architecture and Logic

This document summarizes the investigation into how the Azur Lane Auto Script (ALAS) functions, covering both specific task logic (like Exercises) and the underlying scheduling engine.

## 1. Scheduling & Triggering
The bot uses a priority-based scheduler to decide when to run Exercises.

*   **Refresh Times:** On the English (EN) server, exercises refresh at **00:00, 12:00, and 18:00** (UTC-7). ALAS is hardcoded to listen for these specific "ServerUpdate" timestamps.
*   **Task Priority:** Exercise is a mid-to-high priority task. It runs **after** Commissions, Tactical Class, and Research, but **before** Daily missions, Hard mode, and Event farming.
*   **Retries:** If the task fails or is interrupted, the default `FailureInterval` is 30 minutes.

## 2. Exercise Strategies
The behavior is determined by the `ExerciseStrategy` setting in `module/exercise/exercise.py`:

*   **Aggressive:** Sets `preserve = 0`. The bot will consume all 5-10 available attempts as soon as the task starts.
*   **Rank-Based (e.g., `sun18`, `sat12`):**
    *   **Normal Mode:** Sets `preserve = 5`. The bot only spends attempts in excess of 5 to avoid hitting the 10-attempt cap while maintaining a "reserve" for later.
    *   **Burst Mode:** The bot uses OCR to read the "Time Remaining" in the season. When it enters the chosen window (e.g., 6 hours before the Sunday reset), it changes `preserve` to **0** and dumps all hoarded attempts at once to climb the rankings.

## 3. Execution Flow
The logic follows a nested loop structure:
1.  **Main Loop (`exercise.py`):** OCRs remaining attempts and loops while `remain > preserve`.
2.  **Opponent Selection (`opponent.py`):** Sorts opponents. In `leftmost` mode (recommended), it always targets the far-left opponent (highest rank).
3.  **Combat Execution (`combat.py`):** Enters the battle and monitors HP.
4.  **Automatic Quit (`hp_daemon.py`):** If the fleet's HP falls below a threshold (default **40%**), the bot clicks the Pause button and quits. This prevents a loss and allows the bot to retry the battle without consuming an attempt.
5.  **Refresh Logic:** If the bot cannot beat any of the 4 opponents, it will use one of its 5 daily "New Opponent" refreshes to find easier targets.

## 4. Nuances and Edge Cases
*   **HP Confirmation Timer:** To avoid quitting due to a temporary flicker or a single frame of low HP, the bot uses a `low_hp_confirm_timer` (default **1.5s**). It must see the HP below the threshold consistently for this duration before triggering the quit.
*   **Battle Themes:** The bot is aware of different Azur Lane UI themes (Neon, Christmas, Cyber, etc.). It identifies the current theme by checking the **Pause button's appearance** and adjusts the coordinates for reading health bars accordingly.
*   **'Accept Loss' Fallback:** In the `easiest_else_exp` mode, if the bot fails to beat even the "easiest" target after all 5 refreshes, it will switch to `max_exp` mode and set the `LowHpThreshold` to **0**. This effectively forces the bot to finish the fight and take the loss (and the resulting XP/Merit) rather than wasting the attempt.
*   **Equipment Management:** If a preset is defined in `EXERCISE_FLEET_EQUIPMENT`, the bot will enter the fleet composition screen, enable the "Edit" mode, swap the gear, and then disable "Edit" mode to prevent accidental changes.
*   **Season Timing OCR:** The bot uses a specialized `DatedDuration` OCR that can parse multi-lingual time strings like `10d 01:30:30` (English) or `7日01:30:30` (Japanese/Chinese) to determine how close the season reset is.

## 5. Key Implementation Details
*   **Rank Detection:** The bot **does not** currently read the numerical rank digits (e.g., "Rank 1250"). It relies on the game's internal sorting where the leftmost opponent is always the highest ranked.
*   **Staggering:** Staggering (doing battles one-by-one throughout the day) is not the default behavior. The bot is designed to be efficient: enter, drain attempts to the `preserve` limit, and exit.

## 6. General Bot Architecture & Looping Patterns
Beyond Exercises, the bot operates on a core scheduling engine that governs all tasks:

### The "Hoarding" & Scheduling Mechanism
ALAS uses a sophisticated scheduler rather than simple timers:
*   **Hoarding Mode:** If multiple tasks are overdue, the bot batches them (`is_hoarding_task`) to minimize game restarts and menu navigation.
*   **Server Update Anchors:** Tasks are often anchored to specific server times (e.g., `00:00`). This prevents "timer drift," ensuring tasks don't slowly migrate later into the day over time.
*   **Priority Queue:** All pending tasks are sorted by a `SCHEDULER_PRIORITY` list. Higher-priority tasks (like Commissions) will always preempt lower ones (like Daily farming) if both are due.

### The Task Lifecycle
Every task follows a strict execution loop:
1.  **Selection:** `get_next_task()` identifies the next command based on priority and `next_run` time.
2.  **Orientation:** Takes a screenshot immediately to verify current game state.
3.  **Execution:** Calls the task-specific `run()` method.
4.  **Completion:** Updates the `next_run` timestamp based on success or failure.

### Error Recovery & Reliability
The bot is designed for long-term autonomous operation:
*   **The 3-Strike Rule:** Any task failing 3 times consecutively triggers a "Request Human Takeover" notification and stops the bot.
*   **Stuck Detection:** Tracks `click_record` and `stuck_record`. If the screen is frozen or clicks aren't working, it triggers a full `Restart` task.
*   **Resource Management:** If the next task is far in the future, the bot can be configured to kill the game (`close_game`) to release CPU/RAM/ADB resources.

### Dynamic Config Binding
ALAS uses a "binding" system where settings are context-aware. When the `Exercise` task is active, `self.config` automatically points to the `Exercise` section of the settings, allowing shared logic (like combat) to use task-specific thresholds without complex branching code.

## 7. File Architecture
*   `module/exercise/exercise.py`: Orchestration of the task and preservation logic.
*   `module/exercise/opponent.py`: OCR for fleet power/levels and opponent sorting.
*   `module/exercise/combat.py`: Battle state machine and retry logic.
*   `module/exercise/hp_daemon.py`: Real-time HP calculation from the health bars.
