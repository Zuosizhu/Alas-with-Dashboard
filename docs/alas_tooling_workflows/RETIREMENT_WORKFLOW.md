# Retirement & Enhancement Workflow

## 1. High-Level Summary
This workflow handles the "Dock Full" state. When the dock reaches capacity, the bot must free up space. It can do this either by **Retiring** (scrapping) ships for coins/medals or by **Enhancing** ships (feeding duplicates/fodder to raise stats).

## 2. Core Configuration
These settings in `config_generated.py` (Group: `Retirement` and `Enhance`) control the logic:

*   **`Retirement_RetireMode`** (Default: `'one_click_retire'`): **The Master Branch.**
    *   `'one_click_retire'`: Uses the in-game "Quick Retire" button. Fast, skips enhancement.
    *   `'enhance'`: Attempts to Enhance ships first. If unable, falls back to retiring.
*   **`Enhance_ShipToEnhance`** (Default: `'all'`):
    *   `'all'`: Checks all ships.
    *   `'favourite'`: Only attempts to enhance ships marked as "Favourite".

## 3. Logic Flow

### Triggers: When does this run?
ALAS handles retirement as a **reactive interrupt**. It does not run on a timer; it runs when "blocked":
1.  **Reactive (The Interrupt):** When any task (Combat, Event, Daily) tries to enter a map and the game shows the **"Dock is Full"** popup. ALAS detects this image and immediately diverts to the retirement workflow.
2.  **Proactive (The Buffer):** During `FleetPreparation` (before starting a sortie), ALAS checks the current dock count. If the space remaining is less than the required "safety buffer," it triggers retirement to prevent being interrupted mid-run.
3.  **Post-Task:** Upon collecting rewards from Commissions or Gacha that fill the dock.

### The Logic Tree
Located in `module/retire/retirement.py` -> `handle_retirement()`.
1.  **Detection:** Checks for the "Dock Full" popup or "Low Space" state.
2.  **State Check:** Checks the `_unable_to_enhance` flag.
3.  **Branch 1: One-Click Retire (Default)**
    *   Bot clicks the in-game "Quick Retire" button.
    *   Result: Common/Rare ships are scrapped based on your **in-game** settings.
4.  **Branch 2: Enhance Mode**
    *   Enters the Dock -> Filters for `enhanceable` targets.
    *   Uses the in-game "Recommend" button to fill fodder.
    *   **Fallback (`_unable_to_enhance`):** If enhancement fails to free up enough space (less than 3 slots), it sets a flag to **force a One-Click Retire** on the next run.

## 4. Optimization Principles

To ensure maximum efficiency, the enhancement process follows these guiding principles (Manual and Automated):

*   **[PLANNED ENHANCEMENT] Firepower Fodder Efficiency (Avoiding Over-stacking):**
    *   **The Problem:** Using the in-game "Recommend" (Auto) button often results in "over-stacking." The game may use a Battleship fodder (high Firepower XP) to fill a ship that only needs a small amount of stats to reach its cap, wasting the surplus XP.
    *   **The Proposed Strategy:** High-value Firepower fodder (BB, BC, BM) should be saved for ships with a **large stat deficit**. 
    *   **Manual Tip:** If a ship is nearly capped, use Destroyer (DD) fodder to "top it off" instead of wasting a Battleship.
    *   **Current ALAS Status:** **NOT IMPLEMENTED.** The bot currently relies on the game's "Recommend" button and is prone to this inefficiency. This logic serves as a target for future deterministic tool development.
*   **Aviation Preservation:**
    *   **Goal:** Save Carrier (CV, CVL) fodder specifically for actual Carriers. 
    *   **Reason:** Aviation fodder is relatively rarer than Firepower fodder; wasting a CV to enhance a Destroyer's (DD) minimal stats is considered inefficient.
*   **ALAS Implementation:** Currently, the bot triggers the in-game **Recommend** button. While the game's internal logic attempts to match stats, users should verify their in-game "Recommend" settings to ensure it follows this "Firepower for Firepower" logic.

## 5. Edge Cases & Fallbacks

*   **Aggressive Fallback Sequence:** 
    If the bot attempts to retire ships but `total_retired == 0`, it will not stop. It enters an aggressive retry loop:
    1.  **Reset Filters:** Disables Dock Filters and Favorites.
    2.  **Reset Settings:** It will actually **change your in-game Quick Retire options** (e.g., changing "Keep enough to Max Limit Break" to "Don't Keep").
    3.  **Escalation:** If it still cannot find a single ship to retire after these resets, it raises a `RequestHumanTakeover` and pauses.

*   **"The bot isn't enhancing anyone!"**
    *   **Check Mode:** Ensure `Retirement_RetireMode` is set to `'enhance'`.
    *   **Check Flag:** The bot might be stuck in `_unable_to_enhance` mode if your dock is full of ships you want to keep.
