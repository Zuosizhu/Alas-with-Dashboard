# ALAS Project Todo

## Reference Materials

- [ ] Review `ARCHITECTURE_PATTERNS_REPORT.md` - Helpful architecture overview and design patterns from the upstream ALAS (AzurLaneAutoScript) codebase. Covers task scheduling, device abstraction, UI detection, error handling, stuck detection, and more. Use as inspiration for building our own tools.

## Active Work

<!-- Add active tasks here -->

## Ideas / Backlog

### Dorm Morale Rotation Tool

A first-class tool (possibly integrated directly into ALAS) that optimizes ship girl morale by rotating them through the dorm.

**Requirements:**
- The dorm has two floors, each holding ship girls (12 total across both floors)
- Maximum morale is 150
- When a ship girl reaches ~145+ morale (near cap), swap her out
- Replace her with ship girls from the roster that have the lowest morale
- In the dorm management interface, set filtering to sort by morale and exclude max-level ships
- Ship girls currently assigned to fleets are listed separately (towards the top); rotation candidates come from two groups: those above the fleet listing and those below it
- Runs periodically (every 15-30 minutes or on a sensible interval)
- Goal: keep morale flowing efficiently across the roster rather than capping girls sitting idle at 150

### Exercise Optimization

Improve how exercises are scheduled and scored beyond the current batch-run approach.

**Requirements:**
- Instead of running exercises in batches, run an exercise every couple of hours to spread them out optimally
- Always beat the leftmost opponent (the one that awards the most points based on rank gap)
- Points are awarded based on the difference between your rank and the opponent's rank — bigger gap = more points
- Log the data from each exercise fight:
  - Your rank before the fight
  - The opponent's rank
  - Points gained after the fight
- Use this logged data to inform future optimization (track trends, evaluate strategy)

### Dock Inventory Scanner

A deterministic (non-agent) tool that clicks into the dock and rapidly iterates through all ship girls to build a complete inventory. This should NOT require an LLM agent to drive — it should be scripted click-and-drag in fixed positions with screenshots, so it runs fast.

**Core data to capture per ship girl:**
- Name, level, rarity
- Skills and skill levels
- Gear/equipment loadouts
- Skins owned

**Requirements:**
- Navigate into the dock, then systematically scroll through the entire roster taking screenshots at each position
- Use deterministic screen coordinates (click/drag in the same spots) for speed — no agent decision-making in the loop
- Apply filters or sorting in the dock UI as needed to ensure complete coverage
- Parse the screenshots after capture to extract structured data (OCR, template matching, etc.)
- Store results as a structured inventory (JSON, database, etc.) that can be queried
- Support periodic refresh to track progression over time (level ups, skill upgrades, gear changes)
- Useful for: tracking progress, identifying undergeared/underleveled girls, managing duplicates, optimizing fleet composition

**Stretch goal — Item Inventory:**
- Apply the same screenshot-and-enumerate approach to the item/equipment inventory
- Simpler than ship girls since items can be captured from grid views without clicking into each one
- Goal: a complete game inventory (ships + items) in structured data
