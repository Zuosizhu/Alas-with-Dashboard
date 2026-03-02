# Interactive State Machine Visualization — Plan

> **Created**: 2026-02-17
> **Status**: Draft
> **Depends on**: State Machine extraction (complete), MCP server (operational)

---

## 1. Goal

Build a web-based interactive graph explorer for the ALAS 43-page state machine so that:

- **Developers** can navigate the page graph visually, understand hub-and-spoke topology, and trace navigation paths without reading `page.py` line by line.
- **Debugging** becomes spatial: click a page to see its `check_button`, outgoing links, and navigation constraints — faster than grepping source code.
- **Live operation** (future): connect to the running MCP server to see the bot's current page highlighted in real time, with a breadcrumb trail of recent transitions.

This replaces the static Mermaid diagrams in `STATE_MACHINE_VISUALIZATION.md` with a zoomable, searchable, clickable graph that loads instantly in any browser.

---

## 2. Technology Choice: Cytoscape.js

**Recommendation**: [Cytoscape.js](https://js.cytoscape.org/) (v3.x, ~380 KB minified)

### Why Cytoscape.js over alternatives

| Library | Pros | Cons | Verdict |
|---------|------|------|---------|
| **Cytoscape.js** | Purpose-built for graph exploration; hierarchical/force layouts built-in; first-class node/edge click/hover events; compound nodes for hub grouping; excellent docs | Slightly larger than vis.js | **Winner** |
| D3.js | Maximum flexibility, SVG control | Boilerplate-heavy for graphs; must build selection/zoom/tooltip from scratch; overkill for a structured graph | Too much DIY |
| vis.js Network | Simple defaults, fast setup | Unmaintained (last release 2019); limited layout options; poor TypeScript support | Maintenance risk |
| React Flow | Rich component model | Requires React build pipeline; violates "lightweight / no heavy frameworks" requirement | Over-engineered |
| Mermaid → SVG | Reuses existing diagrams | No true interactivity (click/hover); no zoom/pan; no real-time updates; SVG is static | Too limited |

### Key Cytoscape.js features we use

- **`dagre` layout** (hierarchical top-down) — matches the hub-and-spoke topology naturally.
- **`cy.on('tap', 'node', …)`** — click handler for detail panel.
- **`tippy.js` + `popper.js`** integration — hover tooltips via `cytoscape-popper` extension.
- **Compound nodes** — group pages under their hub (campaign_menu cluster, reward cluster, etc.).
- **Stylesheet selectors** — `.hub { background-color: #4CAF50 }` for role-based coloring.
- **`cy.animate()`** — smooth zoom-to-node on search result click.
- **CDN delivery** — single `<script>` tag, no build step, no `node_modules`.

---

## 3. Architecture

### 3.1 Data Pipeline

```
page.py  ──(Python extraction)──►  graph_data.json  ──(loaded by)──►  index.html
                                                                          │
                                                              Cytoscape.js renders
                                                              interactive graph
```

**Static JSON, not a dynamic API.** Rationale:

- The page graph changes only when `page.py` is edited (rare — handful of times per year).
- A static JSON file means the visualization works offline, from a file:// URL, or served from any static host.
- Re-run the extraction script after editing `page.py` to regenerate the JSON.
- No server dependency for the core visualization. Live state overlay (Phase V2) adds an optional WebSocket connection.

### 3.2 Graph Data Schema (`graph_data.json`)

```json
{
  "metadata": {
    "generated_at": "2026-02-17T12:00:00Z",
    "source": "alas_wrapped/module/ui/page.py",
    "total_pages": 43,
    "total_transitions": 98
  },
  "nodes": [
    {
      "id": "page_main",
      "label": "page_main",
      "check_button": "MAIN_GOTO_FLEET",
      "role": "hub",
      "hub_group": "root",
      "out_degree": 14,
      "in_degree": 30,
      "comment": "Root hub — primary navigation origin"
    }
  ],
  "edges": [
    {
      "id": "page_main->page_campaign_menu",
      "source": "page_main",
      "target": "page_campaign_menu",
      "button": "MAIN_GOTO_CAMPAIGN",
      "bidirectional": false
    }
  ],
  "disabled_edges": [
    {
      "id": "page_shop->page_munitions(disabled)",
      "source": "page_shop",
      "target": "page_munitions",
      "button": "SHOP_GOTO_MUNITIONS",
      "reason": "Prefer academy path; stable background color"
    }
  ],
  "constraints": [
    {
      "description": "Don't enter page_exercise from page_campaign",
      "blocked_source": "page_campaign",
      "blocked_target": "page_exercise",
      "recommended_via": "page_campaign_menu"
    }
  ]
}
```

### 3.3 Role Classification Logic

```
hub           page_main, page_main_white
              (degree centrality > 10, root of the graph)

sub_hub       page_campaign_menu, page_reward, page_reshmenu, page_dormmenu
              (fan-out ≥ 3 to non-main pages)

intermediate  page_campaign, page_event, page_sp, page_academy,
              page_shop, page_meowfficer, page_mail, page_channel,
              page_rpg_stage, page_rpg_story, page_rpg_city, page_hospital,
              page_commission, page_tactical, page_archives
              (has links beyond just GOTO_MAIN)

leaf          page_fleet, page_exercise, page_daily, page_os, page_mission,
              page_guild, page_battle_pass, page_event_list, page_raid,
              page_dock, page_research, page_shipyard, page_meta, page_storage,
              page_dorm, page_private_quarters, page_game_room,
              page_munitions, page_supply_pack, page_build
              (only link is GOTO_MAIN or GOTO_MAIN_WHITE)

special       page_unknown
              (no check_button, fallback state)
```

### 3.4 MCP Integration (Phase V2)

The existing `alas_get_current_state()` MCP tool returns the current page name. For live highlighting:

1. Add a lightweight **WebSocket bridge** in `agent_orchestrator/` that:
   - Connects to the running MCP server (or polls `alas_get_current_state` on an interval).
   - Broadcasts `{ "event": "state_change", "page": "page_reward", "timestamp": "..." }` to WebSocket clients.
2. The HTML viewer opens a WebSocket connection (optional — works without it).
3. On `state_change`, highlight the active node and add to a breadcrumb trail.

This is a thin proxy — no new MCP tools required.

---

## 4. UI Design

### 4.1 Layout

**Primary layout**: `dagre` (hierarchical directed graph) with `rankDir: 'TB'` (top to bottom).

```
                     page_main
                    /    |    \
         campaign_menu  reward  reshmenu  dormmenu  ...direct leaves...
          /  |  \        |  \      |  \      |  \
      campaign exercise commission tactical ...   ...
```

- Hubs at the top, leaves at the bottom — mirrors the mental model of "deeper = more specific."
- `rankSep: 80`, `nodeSep: 40` — compact but readable.
- User can toggle to **`cose` (force-directed)** layout for an alternative view that reveals cluster density.

### 4.2 Color Coding

| Role | Fill | Border | Rationale |
|------|------|--------|-----------|
| `hub` | `#4CAF50` (green) | `#2E7D32` | Main entry points — green = "start here" |
| `sub_hub` | `#2196F3` (blue) | `#1565C0` | Secondary navigation — blue = "routing" |
| `intermediate` | `#AB47BC` (purple) | `#7B1FA2` | Has outgoing links — purple = "connected" |
| `leaf` | `#FF9800` (orange) | `#E65100` | Dead-end pages — orange = "endpoint" |
| `special` | `#9E9E9E` (gray) | `#616161` | page_unknown — gray = "fallback" |
| **Active** (live) | `#F44336` (red) | `#D32F2F` + pulse animation | Current bot position |
| **Trail** (live) | `#FFEB3B` (yellow) border | — | Recently visited pages |

Edge colors:
- Default: `#999` with target arrow
- Bidirectional: `#555`, double arrow
- Disabled: `#ccc`, dashed
- Active transition (live): `#F44336`, animated dash

### 4.3 Panel Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ [🔍 Search: ___________]  [Layout: Dagre ▼]  [Filter: All ▼]  │
├──────────────────────────────────────────┬──────────────────────┤
│                                          │  DETAIL PANEL        │
│                                          │                      │
│          GRAPH CANVAS                    │  page_campaign_menu  │
│       (Cytoscape.js)                     │  ─────────────────   │
│                                          │  Role: sub_hub       │
│    ● page_main                           │  Check: CAMPAIGN_... │
│   / | \                                  │  Hub: campaign       │
│  ●  ●  ●                                │                      │
│  |  |  |                                │  Outgoing (11):       │
│  ●  ●  ●                                │   → page_campaign    │
│                                          │   → page_exercise    │
│                                          │   → page_daily       │
│                                          │   → ...              │
│                                          │                      │
│                                          │  Incoming (3):        │
│                                          │   ← page_main       │
│                                          │   ← page_main_white │
│                                          │   ← page_archives   │
│                                          │                      │
│                                          │  Constraints:         │
│                                          │   ⚠ Don't enter      │
│                                          │   exercise from      │
│                                          │   campaign           │
├──────────────────────────────────────────┴──────────────────────┤
│  Status: Static mode  │  43 pages  │  98 transitions           │
└─────────────────────────────────────────────────────────────────┘
```

**Toolbar features:**
- **Search**: Fuzzy-match page names, highlights matching node and zooms to it.
- **Layout toggle**: Switch between Dagre (hierarchical) and Cose (force-directed).
- **Hub filter dropdown**: Show only pages in a specific hub group (campaign, reward, research, base, all).
- **Reset view**: Re-center and fit graph.

**Detail panel** (right sidebar, 280px):
- Appears on node click.
- Shows: page name, role badge, check_button name, hub group.
- Lists outgoing and incoming edges with button names.
- Shows navigation constraints (if any).
- "Navigate path" button (Phase V2): compute shortest path from page_main and highlight it.

**Tooltips** (on hover):
- Page name, role, out-degree.
- Edge: button name.

---

## 5. Implementation Phases

### Phase V1: Static Interactive Graph (Standalone HTML)

**Scope**: A single self-contained HTML file that loads `graph_data.json` and renders an interactive Cytoscape.js graph. No build tools, no server.

**Deliverables**:
1. `alas_wrapped/tools/extract_page_graph.py` — Python script that imports `page.py` and emits `graph_data.json`.
2. `docs/state_machine/graph_data.json` — Generated graph data.
3. `docs/state_machine/interactive_graph.html` — Standalone HTML viewer (Cytoscape.js from CDN).

**Features**:
- Hierarchical layout (dagre)
- Click node → detail panel
- Hover → tooltip
- Search bar with zoom-to-node
- Hub filter dropdown
- Layout toggle (dagre / cose)
- Color-coded roles
- Disabled edges shown as dashed gray
- Navigation constraint annotations
- Responsive (works on laptop and wide monitor)

**Estimated effort**: Single session (~2-4 hours). The graph data extraction is trivial (iterate `Page.all_pages`), and the HTML is templated Cytoscape.js boilerplate.

**Build command**:
```bash
cd alas_wrapped
.venv/Scripts/python.exe tools/extract_page_graph.py --output ../docs/state_machine/graph_data.json
```

**View**: Open `docs/state_machine/interactive_graph.html` in any browser.

---

### Phase V2: Live State Highlighting (MCP WebSocket)

**Scope**: Add a WebSocket bridge so the visualization can show the bot's current page in real time.

**Deliverables**:
1. `agent_orchestrator/ws_state_bridge.py` — Lightweight WebSocket server that polls `alas_get_current_state()` and broadcasts state changes.
2. Updates to `interactive_graph.html` — Optional WebSocket connection, active node highlighting, breadcrumb trail.

**Features**:
- Connect/disconnect toggle in the toolbar.
- Active page highlighted with red fill + CSS pulse animation.
- Breadcrumb trail: last 10 visited pages shown as yellow-bordered nodes.
- Transition animation: edge briefly flashes when traversed.
- Status bar shows: "Connected to MCP | Current: page_reward | Uptime: 4m32s".

**WebSocket protocol**:
```json
// Server → Client
{ "event": "state_change", "page": "page_reward", "previous": "page_main", "timestamp": 1739800000 }

// Client → Server (future)
{ "command": "goto", "page": "page_commission" }
```

**Architecture**:
```
interactive_graph.html  ←──WebSocket──►  ws_state_bridge.py  ←──MCP stdio──►  alas_mcp_server.py
                                         (polls every 2s)                       (ALAS loaded)
```

**Estimated effort**: 1-2 sessions.

---

### Phase V3: Debugging Tools (Transition History, Error Overlay)

**Scope**: Add debugging overlays for diagnosing navigation failures.

**Deliverables**:
1. Log parser integration — feed `log_parser.py --timeline` output into the graph as an overlay.
2. Error heatmap — pages that frequently trigger `GameStuckError` shown with thicker red borders.
3. Transition history timeline — scrubber at the bottom to replay a session's page transitions.
4. Path inspector — click two nodes to compute and highlight the A* shortest path.

**Features**:
- Import a log file (drag-and-drop or file picker).
- Parse page transitions from log lines: `UI page_main -> page_campaign_menu`.
- Replay transitions in sequence with animation.
- Error count badges on nodes.
- Path length and estimated time between any two nodes.

**Estimated effort**: 2-3 sessions.

---

## 6. File Structure

```
ALAS/
├── alas_wrapped/
│   └── tools/
│       └── extract_page_graph.py      # [NEW] Imports page.py, emits JSON
│                                      # Placement: imports module.ui.page
├── docs/
│   └── state_machine/
│       ├── STATE_MACHINE_VISUALIZATION.md  # [EXISTING] Mermaid diagrams
│       ├── graph_data.json                 # [NEW] Generated graph data (V1)
│       └── interactive_graph.html          # [NEW] Standalone viewer (V1)
├── agent_orchestrator/
│   └── ws_state_bridge.py              # [NEW] WebSocket bridge (V2)
```

**Rationale**:
- `extract_page_graph.py` → `alas_wrapped/tools/` because it `import module.ui.page` (ALAS internal).
- `interactive_graph.html` + `graph_data.json` → `docs/state_machine/` because they are documentation artifacts about the state machine, co-located with the existing Mermaid doc.
- `ws_state_bridge.py` → `agent_orchestrator/` because it is standalone tooling that connects to the MCP server (no ALAS imports).

---

## 7. Data Extraction Script

### `alas_wrapped/tools/extract_page_graph.py`

```python
#!/usr/bin/env python3
"""Extract the ALAS page graph from page.py into a JSON file for visualization.

Usage:
    cd alas_wrapped
    .venv/Scripts/python.exe tools/extract_page_graph.py --output ../docs/state_machine/graph_data.json

Placement: alas_wrapped/tools/ (imports module.ui.page)
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

# Ensure alas_wrapped is on the path
script_dir = os.path.dirname(os.path.abspath(__file__))
alas_root = os.path.dirname(script_dir)  # alas_wrapped/
if alas_root not in sys.path:
    sys.path.insert(0, alas_root)


def classify_role(page_name, out_links, in_count):
    """Classify a page into a role based on its connectivity."""
    if page_name in ("page_main", "page_main_white"):
        return "hub"
    if page_name == "page_unknown":
        return "special"

    # Sub-hubs: fan-out >= 3 to non-main pages
    non_main_out = [dst for dst in out_links if dst not in ("page_main", "page_main_white")]
    if len(non_main_out) >= 3:
        return "sub_hub"

    # Leaves: only link is GOTO_MAIN / GOTO_MAIN_WHITE
    main_targets = {"page_main", "page_main_white"}
    if all(dst in main_targets for dst in out_links):
        return "leaf"

    return "intermediate"


def determine_hub_group(page_name, edges):
    """Determine which hub group a page belongs to based on incoming edges."""
    hub_map = {
        "page_main": "root",
        "page_main_white": "root",
        "page_campaign_menu": "campaign",
        "page_campaign": "campaign",
        "page_exercise": "campaign",
        "page_daily": "campaign",
        "page_event": "campaign",
        "page_sp": "campaign",
        "page_coalition": "campaign",
        "page_os": "campaign",
        "page_archives": "campaign",
        "page_rpg_stage": "campaign",
        "page_rpg_story": "campaign",
        "page_rpg_city": "campaign",
        "page_hospital": "campaign",
        "page_reward": "reward",
        "page_commission": "reward",
        "page_tactical": "reward",
        "page_battle_pass": "reward",
        "page_reshmenu": "research",
        "page_research": "research",
        "page_shipyard": "research",
        "page_meta": "research",
        "page_dormmenu": "base",
        "page_dorm": "base",
        "page_meowfficer": "base",
        "page_academy": "base",
        "page_private_quarters": "base",
        "page_game_room": "base",
        "page_munitions": "base",
        "page_shop": "shop",
        "page_supply_pack": "shop",
        "page_unknown": "special",
    }
    return hub_map.get(page_name, "direct")


def extract_graph():
    """Import Page from page.py and extract the complete graph."""
    from module.ui.page import Page

    nodes = []
    edges = []
    edge_set = set()  # Track (source, target) for bidirectional detection

    # First pass: collect all edges
    raw_edges = []
    for page in Page.iter_pages():
        for destination, button in page.links.items():
            raw_edges.append({
                "source": page.name,
                "target": destination.name,
                "button": type(button).__name__ if hasattr(button, '__name__') else str(button),
            })
            edge_set.add((page.name, destination.name))

    # Second pass: detect bidirectional edges and build final edge list
    for e in raw_edges:
        reverse_exists = (e["target"], e["source"]) in edge_set
        edge_id = f"{e['source']}->{e['target']}"
        edges.append({
            "id": edge_id,
            "source": e["source"],
            "target": e["target"],
            "button": e["button"],
            "bidirectional": reverse_exists,
        })

    # Build nodes
    in_degree = {}
    out_degree = {}
    for e in edges:
        out_degree[e["source"]] = out_degree.get(e["source"], 0) + 1
        in_degree[e["target"]] = in_degree.get(e["target"], 0) + 1

    for page in Page.iter_pages():
        out_links = [dst.name for dst in page.links.keys()]
        od = out_degree.get(page.name, 0)
        ind = in_degree.get(page.name, 0)
        role = classify_role(page.name, out_links, ind)
        hub_group = determine_hub_group(page.name, edges)

        check_btn = None
        if page.check_button is not None:
            check_btn = type(page.check_button).__name__ if hasattr(
                page.check_button, '__name__'
            ) else str(page.check_button)

        nodes.append({
            "id": page.name,
            "label": page.name,
            "check_button": check_btn,
            "role": role,
            "hub_group": hub_group,
            "out_degree": od,
            "in_degree": ind,
        })

    # Known constraints (from code comments in page.py)
    constraints = [
        {
            "description": "Don't enter page_exercise from page_campaign",
            "blocked_source": "page_campaign",
            "blocked_target": "page_exercise",
            "recommended_via": "page_campaign_menu",
        },
        {
            "description": "Don't goto page_commission from page_campaign",
            "blocked_source": "page_campaign",
            "blocked_target": "page_commission",
            "recommended_via": "page_reward",
        },
        {
            "description": "Don't goto page_tactical from page_academy",
            "blocked_source": "page_academy",
            "blocked_target": "page_tactical",
            "recommended_via": "page_reward",
        },
        {
            "description": "Don't goto page_research from page_reward",
            "blocked_source": "page_reward",
            "blocked_target": "page_research",
            "recommended_via": "page_reshmenu",
        },
    ]

    # Known disabled edges (from commented-out code in page.py)
    disabled_edges = [
        {
            "id": "page_shop->page_munitions(disabled)",
            "source": "page_shop",
            "target": "page_munitions",
            "button": "SHOP_GOTO_MUNITIONS",
            "reason": "Prefer academy path; stable background color",
        },
    ]

    graph = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": "alas_wrapped/module/ui/page.py",
            "total_pages": len(nodes),
            "total_transitions": len(edges),
        },
        "nodes": sorted(nodes, key=lambda n: n["id"]),
        "edges": sorted(edges, key=lambda e: e["id"]),
        "disabled_edges": disabled_edges,
        "constraints": constraints,
    }

    return graph


def main():
    parser = argparse.ArgumentParser(
        description="Extract ALAS page graph to JSON for interactive visualization."
    )
    parser.add_argument(
        "--output", "-o",
        default=os.path.join(
            os.path.dirname(__file__), "..", "..", "docs", "state_machine", "graph_data.json"
        ),
        help="Output path for graph_data.json (default: docs/state_machine/graph_data.json)",
    )
    parser.add_argument(
        "--pretty", action="store_true", default=True,
        help="Pretty-print JSON output (default: True)",
    )
    args = parser.parse_args()

    output_path = os.path.abspath(args.output)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    graph = extract_graph()

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2 if args.pretty else None, ensure_ascii=False)

    print(f"Extracted {graph['metadata']['total_pages']} pages, "
          f"{graph['metadata']['total_transitions']} transitions")
    print(f"Written to: {output_path}")


if __name__ == "__main__":
    main()
```

### Script behavior notes

- **Imports `module.ui.page`** — must run from inside `alas_wrapped/` with the ALAS venv active.
- **`check_button` extraction**: uses `str(button)` to capture the asset name. ALAS `Button` objects have a meaningful `__str__` representation. If the repr is unhelpful, a follow-up could extract the `.file` or `.area` attributes.
- **Role classification** is deterministic based on link topology — no hardcoded lists except for the two hub pages and `page_unknown`.
- **Hub group assignment** uses a static map. This is appropriate because the hub structure hasn't changed in years and is unlikely to change frequently. If it does, update the map.
- **Bidirectional detection**: checks whether the reverse edge `(target, source)` exists in the edge set.
- **Re-run when `page.py` changes**: the JSON is a generated artifact; re-run the script and commit the updated JSON.

---

## 8. Interactive Viewer Sketch

### `docs/state_machine/interactive_graph.html` — Structure

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>ALAS State Machine Explorer</title>
  <!-- Cytoscape.js core from CDN -->
  <script src="https://unpkg.com/cytoscape@3/dist/cytoscape.min.js"></script>
  <!-- Dagre layout extension -->
  <script src="https://unpkg.com/dagre@0.8/dist/dagre.min.js"></script>
  <script src="https://unpkg.com/cytoscape-dagre@2/cytoscape-dagre.js"></script>
  <!-- Popper + Tippy for tooltips -->
  <script src="https://unpkg.com/@popperjs/core@2"></script>
  <script src="https://unpkg.com/tippy.js@6"></script>
  <script src="https://unpkg.com/cytoscape-popper@2/cytoscape-popper.js"></script>
  <style>
    /* Full-viewport layout with sidebar */
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
           display: flex; flex-direction: column; height: 100vh; }
    #toolbar { display: flex; align-items: center; gap: 12px; padding: 8px 16px;
               background: #1a1a2e; color: #eee; }
    #toolbar input, #toolbar select { padding: 4px 8px; border-radius: 4px; border: 1px solid #555; }
    #main { display: flex; flex: 1; overflow: hidden; }
    #cy { flex: 1; }
    #detail-panel { width: 300px; background: #f5f5f5; border-left: 1px solid #ddd;
                    padding: 16px; overflow-y: auto; display: none; }
    #detail-panel.active { display: block; }
    #detail-panel h2 { font-size: 16px; margin-bottom: 8px; }
    #detail-panel .role-badge { display: inline-block; padding: 2px 8px; border-radius: 10px;
                                 font-size: 12px; color: #fff; margin-bottom: 12px; }
    #statusbar { padding: 4px 16px; background: #222; color: #aaa; font-size: 12px; }
    .link-list { list-style: none; padding: 0; }
    .link-list li { padding: 4px 0; border-bottom: 1px solid #eee; font-size: 13px; }
    .link-list li:last-child { border-bottom: none; }
    .section-header { font-weight: 600; margin: 12px 0 4px 0; font-size: 13px; color: #555; }
  </style>
</head>
<body>
  <div id="toolbar">
    <label>🔍 <input type="text" id="search" placeholder="Search pages…"></label>
    <label>Layout: <select id="layout-select">
      <option value="dagre">Hierarchical (Dagre)</option>
      <option value="cose">Force-Directed (Cose)</option>
    </select></label>
    <label>Hub: <select id="hub-filter">
      <option value="all">All</option>
      <option value="root">Root</option>
      <option value="campaign">Campaign</option>
      <option value="reward">Reward</option>
      <option value="research">Research</option>
      <option value="base">Base</option>
      <option value="shop">Shop</option>
      <option value="direct">Direct</option>
      <option value="special">Special</option>
    </select></label>
    <button id="reset-btn">Reset View</button>
  </div>
  <div id="main">
    <div id="cy"></div>
    <div id="detail-panel">
      <h2 id="dp-name"></h2>
      <span class="role-badge" id="dp-role"></span>
      <div class="section-header">Check Button</div>
      <div id="dp-check"></div>
      <div class="section-header">Hub Group</div>
      <div id="dp-hub"></div>
      <div class="section-header" id="dp-out-header">Outgoing</div>
      <ul class="link-list" id="dp-out-links"></ul>
      <div class="section-header" id="dp-in-header">Incoming</div>
      <ul class="link-list" id="dp-in-links"></ul>
      <div class="section-header" id="dp-constraints-header" style="display:none">Constraints</div>
      <ul class="link-list" id="dp-constraints"></ul>
    </div>
  </div>
  <div id="statusbar">
    <span id="sb-status">Static mode</span> │
    <span id="sb-pages">–</span> pages │
    <span id="sb-edges">–</span> transitions
  </div>

  <script>
    // Graph data loaded from JSON sidecar
    let graphData = null;
    let cy = null;

    async function init() {
      const resp = await fetch('graph_data.json');
      graphData = await resp.json();
      document.getElementById('sb-pages').textContent = graphData.metadata.total_pages;
      document.getElementById('sb-edges').textContent = graphData.metadata.total_transitions;
      buildGraph();
      bindEvents();
    }

    // ... (Cytoscape initialization, event handlers, detail panel, search, filter, layout toggle)
    // Full implementation in Phase V1 build session.

    init();
  </script>
</body>
</html>
```

> The sketch above shows the HTML skeleton. The full `<script>` block (Cytoscape initialization, stylesheet, event handlers, detail panel population, search, filter, layout toggle) will be implemented during the Phase V1 build session. The structure is intentionally simple — a single file, no build step, no dependencies beyond CDN scripts.

---

## 9. Acceptance Criteria

### Phase V1

- [ ] `extract_page_graph.py` runs without errors and produces valid JSON.
- [ ] JSON contains all 43 pages and 98 transitions from `page.py`.
- [ ] HTML opens in Chrome/Firefox and renders the graph in < 2 seconds.
- [ ] Click any node → detail panel shows check_button, links, role, hub group.
- [ ] Search "campaign" → highlights and zooms to matching nodes.
- [ ] Hub filter "reward" → shows only reward-group nodes + their edges.
- [ ] Layout toggle switches between dagre and cose without errors.
- [ ] Works from `file://` URL (no web server required).

### Phase V2

- [ ] WebSocket bridge connects to running MCP server.
- [ ] Active page node is red-highlighted within 3 seconds of state change.
- [ ] Breadcrumb trail shows last 10 pages visited.
- [ ] Graceful degradation: visualization works fully when WebSocket is unavailable.

### Phase V3

- [ ] Log file can be loaded via file picker or drag-and-drop.
- [ ] Transition replay plays back page changes with animation.
- [ ] Error heatmap shows GameStuckError frequency per node.
- [ ] Path inspector computes shortest path between any two selected nodes.

---

## 10. Open Questions

1. **Button names in JSON**: `str(button)` on ALAS `Button` objects produces `Button(file=..., area=(...), ...)`. Should we extract just the variable name (like `MAIN_GOTO_CAMPAIGN`) instead? This requires inspecting the variable name from `page.py` source or from ALAS asset module `__dict__`. Decision: investigate during V1 build, use best available repr.

2. **Offline CDN**: For air-gapped use, should we vendor Cytoscape.js into the repo? The minified JS is ~380 KB. Decision: defer until needed; CDN is fine for development.

3. **`graph_data.json` in version control**: Should the generated JSON be committed? Pro: anyone can open the HTML without running the extraction script. Con: generated artifact. Decision: commit it — it changes rarely and enables zero-setup viewing.

4. **WebSocket bridge auth**: The MCP server runs locally. The WS bridge should bind to `localhost` only. No auth needed for V2.
