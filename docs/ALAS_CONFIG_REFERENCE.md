# ALAS Configuration Explainer

This document outlines the configuration options available in ALAS (Azur Lane Auto Script), based on the `template.json` structure and the `AzurLaneConfig` class in the codebase.

## Configuration Groups

The configurations are grouped into several logical categories based on their function within the game or the bot itself.

### 1. Core System & Emulator
Settings related to the bot's operation, emulator connection, and error handling.
*   **`Alas`**: Central settings for the bot.
    *   `Emulator`: Serial, package name, control methods (MaaTouch), screenshot methods.
    *   `Error`: Error handling, saving screenshots on error.
    *   `Optimization`: Screenshot intervals, task hoarding (running multiple tasks in a row).
    *   `DropRecord`: Stats collection (AzurStats).
*   **`Restart`**: Scheduler for restarting the bot/emulator periodically.

### 2. Dashboard
*   **`Dashboard`**: Configuration for the web dashboard resource display (Oil, Coin, Gems, etc.), defining limits and display colors.

### 3. General Game Management
Routine daily tasks and general account management.
*   **`General`**: Ship management settings.
    *   `Retirement`: Automatic retiring of Common/Rare ships to save dock space.
    *   `Enhance`: Feeding ships to improve stats.
*   **`Dorm`**: Collecting coins/oil from the dorm, feeding ships (including food filters like "Curry" or "Full Course") to maintain high morale.
*   **`Meowfficer`**: Buying and training Meowfficers (cat-like support units).
*   **`Guild`**: Guild logistics (donations) and operations.
*   **`Reward`**: Collecting mail, trade licenses, and mission rewards.
*   **`Awaken`**: Awakening ships to higher levels (Level 100+).
*   **`Daily`**: Daily raid missions (Escort, Advance, Fierce Assault, etc.).
*   **`Freebies`**: Collecting free packs, battle pass rewards, and data keys.
*   **`PrivateQuarters`**: Interaction with the secretary ship (buying gifts, touch) to raise affinity.

### 4. Logistics & Development
Long-term progression and resource acquisition tasks.
*   **`Commission`**: Scheduling commissions (timed resource gathering missions). The bot can filter by reward type (Cube, Oil, Gems).
*   **`Tactical`**: Tactical class skill training filters (prioritizing specific books or ship types).
*   **`Research`**: Research Academy priority filters (Series, Ship, Type) to acquire blueprints for PR/DR ships.
*   **`Shipyard`**: Priority Research (PR/DR) ship development tasks (spending coins/cubes).
*   **`Gacha`**: Automatic ship building.
*   **`ShopFrequent`**: General shop purchases (refreshing, buying food/books).
*   **`ShopOnce`**: Buying from Guild, Medal, Merit, and Core shops.

### 5. PvP & Minigames
*   **`Exercise`**: PvP Exercises. Includes strategies for opponent selection (e.g., "max_exp" to fight strong opponents for more XP) and low HP resets (retreating before losing to save rank).
*   **`Minigame`**: Automation for temporary event minigames.

### 6. Operation Siren (OpSi)
Extensive configuration for the open-world Operation Siren mode. This mode uses no Oil but requires Action Points (AP).
*   **`OpsiGeneral`**: General OpSi settings (AP limits, repair thresholds).
*   **`OpsiExplore`**: Zone exploration logic (clearing map tiles).
*   **`OpsiDaily`**: Daily OpSi missions.
*   **`OpsiShop` / `OpsiVoucher`**: Buying items from OpSi shops (Ports).
*   **`OpsiAshBeacon` / `OpsiAshAssist`**: META showdown (Ashes) configuration. Fighting boss instances shared with friends/guild.
*   **`OpsiObscure` / `OpsiAbyssal` / `OpsiStronghold`**: High-difficulty coordinates and strongholds.
*   **`OpsiMonthBoss`**: Arbiter (Monthly Boss) challenges.
*   **`OpsiArchive`**: Siren logger archives.
*   **`OpsiMeowfficerFarming` / `OpsiHazard1Leveling`**: Specific farming strategies for items or XP.
*   **`OpsiCrossMonth`**: Logic for the monthly reset of OpSi maps.

### 7. Internal / Daemon
*   **`Daemon` / `OpsiDaemon` / `EventStory`**: Background tasks and logic usually not modified by standard users.

---

## Combat & Campaign Configurations (*Fleet-like Configs*)

These sections control how the bot fights battles. They share a common, complex structure defining fleets, formations, emotional states, and stop conditions.

**Modules with this structure:**
*   **`Main`**, **`Main2`**, **`Main3`** (Standard Campaign: Chapters 1-15)
*   **`Event`**, **`Event2`** (Major Events)
*   **`EventA`** through **`EventSp`** (Various Event Types)
*   **`WarArchives`** (Archived Events)
*   **`Raid`**, **`RaidDaily`** (Raid Events)
*   **`Coalition`**, **`CoalitionSp`** (Coalition/SP Events)
*   **`GemsFarming`** (Specific farming mode)
*   **`MaritimeEscort`**

> **Note:** `Hard` and `Hospital` share *some* of these traits but are often simplified.

### Explainer: The "Fleet-like" Configuration Object

Modules marked above generally contain the following shared subsections, mapping to in-game mechanics:

1.  **`Scheduler`**:
    *   Controls *when* this task runs.
    *   `Enable`: Turn the task on/off.
    *   `SuccessInterval` / `FailureInterval`: Cooldown in minutes after a run.

2.  **`Campaign`**:
    *   `Name`: Map ID (e.g., "12-4" for Chapter 12 Stage 4, "D3" for Event Hard Mode Stage 3).
    *   `Mode`: "normal" or "hard".
    *   `UseAutoSearch`: Toggles the in-game "Auto Search" feature (pathfinding).
    *   **`AmbushEvade`**: Logic to evade "Ambush Fleets" which waste ammo/oil if fought unnecessarily.

3.  **`Fleet`** (The Core Combat Config):
    *   **`Fleet1` / `Fleet2`**: Index of the fleet to use (1-6). In Azur Lane, you have multiple preset fleets.
    *   **`Fleet1Formation`**: Combat formation (e.g., "double_line" for evasion, "circular" for AA).
    *   **`Fleet1Mode`**: Battle mode ("combat_auto" for auto-battle).
    *   **`FleetOrder`**: Strategy for swapping fleets.
        *   `fleet1_mob_fleet2_boss`: **Standard Strategy**. Use Fleet 1 (Mob Fleet) to clear escort enemies and Fleet 2 (Boss Fleet) to kill the boss. This conserves the Boss Fleet's ammo and HP.

4.  **`Submarine`**:
    *   `Fleet`: Submarine fleet index.
    *   `Mode`: When to summon subs ("do_not_use", "every_combat", "boss_combat"). Subs cost extra Oil but deal massive damage.
    *   `DistanceToBoss`: When using auto-search, how close to boss to idle subs (hunting range).

5.  **`Emotion`** (Morale Management):
    *   **Context**: "Emotion" refers to ship Morale (0-150). High morale (>119) gives +20% XP. Low morale (<30) loses affinity and halves XP.
    *   `Mode`: "calculate" (predict morale based on battles).
    *   `Fleet1Control`: **`prevent_yellow_face`**. Stops the bot if morale drops below 40 (Yellow Face) to prevent affinity loss.
    *   `Fleet1Recover`: Strategy for recovering morale (e.g., "not_in_dormitory"). Ships in the Dorm recover morale much faster.

6.  **`HpControl`**:
    *   `UseEmergencyRepair`: Use the free emergency repair tool (available on some ships/maps) if HP is low.
    *   `UseLowHpRetreat`: **Critical for safety**. Retreats the fleet if a ship is about to sink (preventing loss of the battle/S-rank).
    *   `HpBalanceThreshold`: Threshold for balancing fleet HP (e.g., moving damaged ships to safer positions).

7.  **`StopCondition`**:
    *   Defines when the bot should *stop* running this task.
    *   `OilLimit`: Stop after consuming X oil. **Oil** is the stamina currency for sorties.
    *   `RunCount`: Stop after X runs.
    *   `GetNewShip`: Stop if a new ship drops (useful for farming specific map drops).
    *   `ReachLevel`: Stop if a ship reaches a certain level (for leveling alt ships).

8.  **`EnemyPriority`**:
    *   Logic for which enemies to attack first on the map (e.g., "Large Fleet" > "Small Fleet"). Large fleets give more XP but are harder.

---

## Research Summary

**Objective:**
Analyze the ALAS configuration structure to identify all available options, group them logically, and specifically detail the complex 'Fleet-like' configuration objects. Verify this understanding against the codebase and actual game mechanics of Azur Lane.

**Actions Taken:**
1.  **Configuration Analysis**: Scanned ALAS/alas_wrapped/config/template.json to map the full hierarchy of settings available to the bot.
2.  **Categorization**: Grouped these settings into logical domains (Core System, General Management, Logistics, PvP, Operation Siren, etc.).
3.  **Code Verification**: Examined las.py and module/config/config.py to confirm how these configurations are loaded (AzurLaneConfig) and bound to specific tasks.
4.  **Context Research**: Researched Azur Lane gameplay mechanics (Fleets, Oil, Morale/Emotion, Operation Siren) to provide accurate context for specific settings like prevent_yellow_face and leet1_mob_fleet2_boss.
5.  **Documentation**: Compiled these findings into this document, refining the explanations to bridge the gap between technical config keys and their in-game purpose.

---
