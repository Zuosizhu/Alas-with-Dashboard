# Feature Ideas

Detailed requirements for planned capabilities. Referenced from [todo.md](../todo.md).

---

## Dorm Morale Rotation Tool

A first-class tool (possibly integrated directly into ALAS) that optimizes ship girl morale by rotating them through the dorm.

### Context

The dorm has two floors, each holding ship girls (12 total across both floors). Ship girls passively gain morale while in the dorm, up to a maximum of 150. Once a girl is near cap (~145+), she's wasting a dorm slot that could be recovering someone else. Currently there is no automated rotation — girls just sit there at max morale.

### Requirements

- When a ship girl in the dorm reaches ~145+ morale, swap her out for a low-morale girl from the roster
- In the dorm management interface, set filtering to sort by morale and exclude max-level ships
- Ship girls currently assigned to fleets are listed separately (towards the top of the list); rotation candidates come from two groups — those above the fleet listing and those below it
- Both dorm floors need to be managed (two groups of slots)
- Runs periodically (every 15-30 minutes, or whatever interval makes sense given morale gain rates)
- Goal: keep morale flowing efficiently across the roster rather than letting girls sit idle at 150

---

## Exercise Optimization

Improve how exercises are scheduled and scored beyond the current batch-run approach.

### Context

The current implementation runs exercises in batches. This is suboptimal because exercises regenerate over time, and spreading them out allows you to always fight opponents at the best possible rank gap. Points are awarded based on the difference between your rank and the opponent's rank — beating someone much higher-ranked than you gives more points. The leftmost opponent in the exercise list represents the biggest rank gap.

### Requirements

- Instead of running exercises in batches, run an exercise every couple of hours to spread them out optimally
- Always beat the leftmost opponent (the one that awards the most points based on rank gap)
- Points are awarded based on the difference between your rank and the opponent's rank — bigger gap = more points
- Log the data from each exercise fight:
  - Your rank before the fight
  - The opponent's rank
  - Points gained after the fight
- Use this logged data to inform future optimization (track trends, evaluate strategy over time)

---

## Dock Inventory Scanner

A deterministic (non-agent) tool that clicks into the dock and rapidly iterates through all ship girls to build a complete inventory of the account.

### Context

There is currently no way to get a structured view of everything you own in the game. This tool would systematically screenshot and parse the dock to produce a queryable dataset. This should NOT require an LLM agent to drive — it should be scripted click-and-drag at fixed screen positions with screenshots, so it runs fast. The agent is only needed to interpret the results afterward, not to perform the scanning.

### Core data to capture per ship girl

- Name, level, rarity
- Skills and skill levels
- Gear/equipment loadouts
- Skins owned

### Requirements

- Navigate into the dock, then systematically scroll through the entire roster, taking screenshots at each position
- Use deterministic screen coordinates (click/drag in the same spots) for speed — no agent decision-making in the scanning loop
- Apply filters or sorting in the dock UI as needed to ensure complete coverage
- Parse the screenshots after capture to extract structured data (OCR, template matching, etc.)
- Store results as a structured inventory (JSON, database, or similar) that can be queried
- Support periodic refresh to track progression over time (level ups, skill upgrades, gear changes)
- Useful for: tracking progress, identifying undergeared/underleveled girls, managing duplicates, optimizing fleet composition

### Stretch goal: Item Inventory

- Apply the same screenshot-and-enumerate approach to the item/equipment inventory
- Simpler than ship girls since items can be captured from grid views without clicking into each one
- Goal: a complete game inventory (ships + items) in structured data

---

## Equipment Outfitter

A tool to manage and redistribute limited best-in-slot gear across ship girls depending on what content is being run.

### Context

The best equipment in the game exists in limited quantities. Different game modes (exercises, campaign fleets, events, etc.) may need the same gear on different ship girls. Currently there's no automated way to shuffle gear around — you have to manually unequip and re-equip pieces, which is tedious and error-prone. This tool would let you define equipment "loadouts" or priorities and have the system swap gear between ship girls as needed.

### Requirements

- Know what gear you have (depends on Dock Inventory Scanner being built first)
- Track which ship girls need which equipment for which game modes (exercises vs. fleet sorties, etc.)
- Swap equipment between ship girls programmatically — unequip from one, equip on another
- Leverage ALAS's existing deterministic click infrastructure (known screen coordinates, button positions) for speed — no LLM agent needed in the loop
- Many of these tools share a common principle: ALAS already knows the click locations, so the automation can be fast and scripted rather than requiring the agent to visually interpret every screen

### Design note

This is a higher-level tool that builds on the inventory data from the Dock Inventory Scanner. It likely comes after that foundation is in place.
