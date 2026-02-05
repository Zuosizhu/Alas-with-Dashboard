# Meowfficer (Cat) Workflow

## 1. High-Level Summary
This workflow governs the management of Meowfficers (Cats), specifically the automation of **Enhancement** (feeding cats to other cats for XP) and **Training**. It ensures that specific "target" cats receive XP while carefully selecting "fodder" cats to be consumed based on level and rarity filters.

## 2. Core Configuration
These settings in `config_generated.py` (Group: `MeowfficerTrain`) control the logic:

*   **`MeowfficerTrain_Enable`** (Default: `False`): Master switch. Must be `True` for any of this to run.
*   **`MeowfficerTrain_EnhanceIndex`** (Default: `1`): The slot number (1-12) of the *Target* cat who will receive XP.
*   **`MeowfficerTrain_MaxFeedLevel`** (Default: `5`): **Critical Safety Flag.** The bot will **NOT** select any cat as fodder if its level is higher than this value.
*   **`MeowfficerTrain_Mode`** (Default: `'seamlessly'`):
    *   `'seamlessly'`: Checks for enhancement opportunities whenever the bot is in the main loop.
    *   `'once_a_day'`: Runs only once per daily reset.

## 3. Logic Flow

### Triggers: When does this run?
Unlike Ship Retirement (which is reactive), Meowfficer Training is **scheduled/proactive**:
1.  **The Main Loop:** When ALAS is between tasks (returning to the Home screen) and the `MeowfficerTrain` task is next in the queue.
2.  **Mode-Based Execution:**
    *   `seamlessly`: The bot checks if enhancement is possible every time it cycles through its main task list.
    *   `once_a_day`: The bot only executes this once per 24 hours (after the daily reset).
3.  **Daemon Mode:** If the bot is idling in "Daemon" mode, it will periodically enter the Meowfficer screen to check for training completions or enhancement fodder.

### Phase 1: Enhancement (Feeding)
Located in `module/meowfficer/enhance.py`.

1.  **Pre-Flight Checks:**
    *   Is `MeowfficerTrain_EnhanceIndex` between 1 and 12?
    *   **Coin Check:** Do we have at least **1000 Coins**? (If `< 1000`, Skip).

2.  **Target Selection:**
    *   The bot selects the cat at `MeowfficerTrain_EnhanceIndex`.
    *   **Level Check:** It OCRs the target cat's level.
        *   If **Level 30 (Max)**: The bot increments `MeowfficerTrain_EnhanceIndex` by 1 to start training the *next* cat in the list.
        *   If `EnhanceIndex` goes > 12, it disables `MeowfficerTrain_Enable`.

3.  **Fodder Scanning (`meow_feed_scan`):**
    *   The bot enters the "Feed" (Enhance) screen.
    *   It scans the 4x3 grid of available cats.
    *   **Filtering Logic (The "Retire" Logic):**
        *   It ignores empty slots.
        *   It ignores cats already selected (green checkmark).
        *   **It reads the Level of every candidate cat.**
        *   **CRITICAL:** If `Candidate_Level > MeowfficerTrain_MaxFeedLevel` (Default 5), the cat is **SKIPPED**.
    *   It selects all valid candidates.

4.  **Execution (The Loop):**
    *   If candidates > 0: It clicks "Confirm".
    *   **Loop Condition:** After each enhancement, it re-checks if coins are still **> 1000**. If they drop below this threshold mid-run, it will stop immediately.
    *   If candidates == 0: It exits the enhancement loop.

### Phase 2: Buying & Training
Located in `module/meowfficer/train.py`.

1.  **Buying:** Checks `Meowfficer_BuyAmount`. If > 0, buys cat boxes from the shop.
2.  **Training:** checks if the daily free training or paid training slots are available and assigns cats.

## 4. Edge Cases & Fallbacks

*   **"My bot isn't retiring cats!"**
    *   **Cause:** Your "fodder" cats are likely Level 6 or higher (often happens if they were left in the Cattery/Dorm).
    *   **Fix:** Raise `MeowfficerTrain_MaxFeedLevel` to `30` to allow the bot to consume any cat regardless of level.

*   **"My bot stopped after maxing one cat."**
    *   **Feature:** The bot automatically moves to the next index (`Index + 1`). If you only wanted to train Cat #1 and stop, this auto-increment logic might surprise you.
