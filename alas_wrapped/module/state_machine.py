from collections import deque
from typing import Any, Dict, List, Optional, Set

from module.ui.ui import UI
from module.ui.page import Page, page_main, page_dorm, page_commission, page_research, page_shop, page_guild
from module.tool import Tool
from module.dorm.dorm import RewardDorm
from module.dorm.buy_furniture import BuyFurniture
from module.commission.commission import RewardCommission
from module.research.research import RewardResearch
from module.shop.shop_general import GeneralShop_250814 as GeneralShop
from module.guild.lobby import GuildLobby
from module.freebies.mail_white import MailWhite as Mail

class StateMachine:
    """Runtime UI state machine wrapper plus workflow validation helpers.

    IMPORTANT:
    - `dry_run_workflow(...)` validates against this *instance*'s registered tool map
      (`self.tools`) and reachable page links from current runtime objects.
    - `validate_workflow_spec_against_graph(...)` is static/spec-level analysis using
      `Page.all_pages` and `tool_specs()` declarations. It is for harness design
      validation and does not execute gameplay actions.
    """
    DAILY_BASE_SWEEP_STEPS = [
        {"state": "page_main", "tool": "main.collect_mail", "arguments": {}},
        {"state": "page_dorm", "tool": "dorm.collect_rewards", "arguments": {}},
        {"state": "page_dorm", "tool": "dorm.feed_ships", "arguments": {}},
        {"state": "page_commission", "tool": "commission.run", "arguments": {}},
        {"state": "page_research", "tool": "research.run", "arguments": {}},
        {"state": "page_shop", "tool": "shop.run", "arguments": {}},
        {"state": "page_guild", "tool": "guild.collect_lobby_rewards", "arguments": {}},
    ]

    @staticmethod
    def tool_specs() -> List[Dict[str, Any]]:
        return [
            {
                "name": "main.collect_mail",
                "description": "Collects mail rewards.",
                "parameters": None,
                "states": ["page_main"],
            },
            {
                "name": "dorm.collect_rewards",
                "description": "Collects all coins and loves in the dorm.",
                "parameters": None,
                "states": ["page_dorm"],
            },
            {
                "name": "dorm.feed_ships",
                "description": "Feeds the ships in the dorm.",
                "parameters": None,
                "states": ["page_dorm"],
            },
            {
                "name": "dorm.buy_furniture",
                "description": "Buys time-limited furniture from the shop.",
                "parameters": [
                    {
                        "name": "buy_option",
                        "type": "str",
                        "description": "Can be 'all' or 'set'.",
                    }
                ],
                "states": ["page_dorm"],
            },
            {
                "name": "dorm.get_ship_count",
                "description": "Gets the number of ships currently in the dorm.",
                "parameters": None,
                "states": ["page_dorm"],
            },
            {
                "name": "commission.run",
                "description": "Receives rewards from completed commissions and starts new ones.",
                "parameters": None,
                "states": ["page_commission"],
            },
            {
                "name": "research.run",
                "description": "Handles receiving completed research, starting new projects, and filling the queue.",
                "parameters": None,
                "states": ["page_research"],
            },
            {
                "name": "shop.run",
                "description": "Buys items from the general shop based on user filters.",
                "parameters": None,
                "states": ["page_shop"],
            },
            {
                "name": "guild.collect_lobby_rewards",
                "description": "Collects rewards from guild reports in the lobby.",
                "parameters": None,
                "states": ["page_guild"],
            },
            {
                "name": "workflow.daily_base_sweep",
                "description": "Runs a deterministic base-management sweep (mail/dorm/commission/research/shop/guild).",
                "parameters": [
                    {
                        "name": "continue_on_failure",
                        "type": "bool",
                        "description": "Continue remaining steps after a failure if true.",
                    }
                ],
                "states": ["*"],
            },
        ]


    @staticmethod
    def semantic_state_graph() -> Dict[str, List[str]]:
        """Return semantic page-edge graph from `Page.all_pages` links only.

        This is a static graph view (no device actions) suitable for audit tooling.
        """
        graph: Dict[str, List[str]] = {}
        for page in Page.all_pages.values():
            graph[page.name] = sorted([neighbor.name for neighbor in page.links.keys()])
        return graph

    @staticmethod
    def _semantic_find_path(graph: Dict[str, List[str]], start_state: str, destination_state: str) -> Optional[List[str]]:
        """Find shortest path between semantic states using BFS over graph names."""
        if start_state == destination_state:
            return [start_state]

        queue = deque([(start_state, [start_state])])
        visited = {start_state}

        while queue:
            current, path = queue.popleft()
            for neighbor in graph.get(current, []):
                if neighbor in visited:
                    continue
                next_path = path + [neighbor]
                if neighbor == destination_state:
                    return next_path
                visited.add(neighbor)
                queue.append((neighbor, next_path))

        return None

    @staticmethod
    def tool_state_index_from_specs() -> Dict[str, set]:
        """Index tool->declared states from `tool_specs()` for static validation."""
        index: Dict[str, set] = {}
        for spec in StateMachine.tool_specs():
            states = spec.get("states") or []
            if "*" in states:
                index[spec["name"]] = {"*"}
            else:
                index[spec["name"]] = set(states)
        return index

    @staticmethod
    def validate_workflow_spec_against_graph(
        steps: List[Dict[str, Any]],
        start_state: str = "page_main",
    ) -> Dict[str, Any]:
        """Static workflow lint: states, tool declarations, and semantic reachability.

        This does NOT run ALAS handlers. It validates proposed harness definitions
        against current code declarations to catch mismatches early.
        """
        graph = StateMachine.semantic_state_graph()
        tool_states = StateMachine.tool_state_index_from_specs()

        if start_state not in graph:
            return {"success": False, "error": f"Unknown start_state: {start_state}", "steps": []}

        current = start_state
        results: List[Dict[str, Any]] = []

        for idx, step in enumerate(steps, start=1):
            target = step.get("state")
            tool = step.get("tool")
            step_result = {
                "step": idx,
                "from_state": current,
                "target_state": target,
                "tool": tool,
                "path": None,
                "reachable": False,
                "error": None,
            }

            if target not in graph:
                step_result["error"] = f"Unknown target state: {target}"
                results.append(step_result)
                return {"success": False, "error": "Workflow contains unknown state", "steps": results}

            if tool not in tool_states:
                step_result["error"] = f"Unknown tool: {tool}"
                results.append(step_result)
                return {"success": False, "error": "Workflow contains unknown tool", "steps": results}

            allowed_states = tool_states[tool]
            if "*" not in allowed_states and target not in allowed_states:
                step_result["error"] = f"Tool {tool} is not declared for state {target}"
                results.append(step_result)
                return {"success": False, "error": "Workflow contains tool/state mismatch", "steps": results}

            path = StateMachine._semantic_find_path(graph, current, target)
            step_result["path"] = path
            if path is None:
                step_result["error"] = f"No semantic path from {current} to {target}"
                results.append(step_result)
                return {"success": False, "error": "Workflow contains unreachable state transition", "steps": results}

            step_result["reachable"] = True
            results.append(step_result)
            current = target

        return {"success": True, "error": None, "steps": results}

    def __init__(self, ui: UI):
        """
        Initializes the StateMachine with a UI instance.

        Args:
            ui (UI): An instance of the UI class.
        """
        self.ui = ui
        self.tools = self._register_tools()
        self.tool_registry = self._build_tool_registry(self.tools)

    def get_current_state(self) -> Page:
        """
        Returns the current state (page) of the bot.

        Returns:
            Page: The current page object.
        """
        return self.ui.ui_get_current_page()

    def get_possible_actions(self, state: Optional[Page] = None) -> List[Page]:
        """
        Returns a list of possible next states from the given state.
        If no state is provided, it uses the current state.

        Args:
            state (Page, optional): The state to get actions for. Defaults to None.

        Returns:
            List[Page]: A list of possible destination pages.
        """
        if state is None:
            state = self.get_current_state()
        return list(state.links.keys())

    def transition(self, destination: Page):
        """
        Transitions the bot to the given state.

        Args:
            destination (Page): The destination page to transition to.
        """
        self.ui.ui_goto(destination)

    def get_all_states(self) -> List[Page]:
        """
        Returns a list of all possible states in the state machine.

        Returns:
            List[Page]: A list of all page objects.
        """
        return list(Page.all_pages.values())

    def _register_tools(self):
        """
        Registers all the tools for all the states.
        """
        dorm_handler = RewardDorm(self.ui.config, self.ui.device)
        buy_furniture_handler = BuyFurniture(self.ui.config, self.ui.device)
        commission_handler = RewardCommission(self.ui.config, self.ui.device)
        research_handler = RewardResearch(self.ui.config, self.ui.device)
        shop_handler = GeneralShop(self.ui.config, self.ui.device)
        guild_handler = GuildLobby(self.ui.config, self.ui.device)
        mail_handler = Mail(self.ui.config, self.ui.device)

        return {
            page_main: [
                Tool(
                    name="main.collect_mail",
                    description="Collects mail rewards.",
                    execute=mail_handler.run
                ),
                Tool(
                    name="workflow.daily_base_sweep",
                    description="Runs a deterministic base-management sweep (mail/dorm/commission/research/shop/guild).",
                    execute=self.run_daily_base_sweep,
                    parameters=[
                        {
                            "name": "continue_on_failure",
                            "type": "bool",
                            "description": "Continue remaining steps after a failure if true.",
                        }
                    ]
                )
            ],
            page_dorm: [
                Tool(
                    name="dorm.collect_rewards",
                    description="Collects all coins and loves in the dorm.",
                    execute=dorm_handler.dorm_collect
                ),
                Tool(
                    name="dorm.feed_ships",
                    description="Feeds the ships in the dorm.",
                    execute=dorm_handler.dorm_feed
                ),
                Tool(
                    name="dorm.buy_furniture",
                    description="Buys time-limited furniture from the shop.",
                    execute=buy_furniture_handler.buy_furniture_run,
                    parameters=[
                        {"name": "buy_option", "type": "str", "description": "Can be 'all' or 'set'."}
                    ]
                ),
                Tool(
                    name="dorm.get_ship_count",
                    description="Gets the number of ships currently in the dorm.",
                    execute=dorm_handler.get_dorm_ship_amount
                )
            ],
            page_commission: [
                Tool(
                    name="commission.run",
                    description="Receives rewards from completed commissions and starts new ones.",
                    execute=commission_handler.run
                )
            ],
            page_research: [
                Tool(
                    name="research.run",
                    description="Handles receiving completed research, starting new projects, and filling the queue.",
                    execute=research_handler.run
                )
            ],
            page_shop: [
                Tool(
                    name="shop.run",
                    description="Buys items from the general shop based on user filters.",
                    execute=shop_handler.run
                )
            ],
            page_guild: [
                Tool(
                    name="guild.collect_lobby_rewards",
                    description="Collects rewards from guild reports in the lobby.",
                    execute=guild_handler.guild_lobby
                )
            ],
        }



    def _state_tools(self, state: Page) -> Set[str]:
        """Return tool names actually bound to a runtime state in this instance."""
        return {tool.name for tool in self.tools.get(state, [])}

    def _tool_available_in_state(self, tool_name: str, state: Page) -> bool:
        return tool_name in self._state_tools(state)

    def analyze_workflow_failure_point(self, steps: List[Dict[str, Any]], start_state: str = "page_main") -> Dict[str, Any]:
        """Return first blocking step from runtime dry-run validation output."""
        dry_run = self.dry_run_workflow(steps=steps, start_state=start_state)
        if dry_run["success"]:
            return {"success": True, "failure_point": None, "dry_run": dry_run}

        steps_result = dry_run.get("steps", [])
        failure_step = steps_result[-1] if steps_result else None
        return {
            "success": False,
            "failure_point": failure_step,
            "dry_run": dry_run,
        }

    @staticmethod
    def _resolve_state(states: Dict[str, Page], name: str) -> Optional[Page]:
        return states.get(name)

    @staticmethod
    def _find_path(start: Page, destination: Page) -> Optional[List[str]]:
        if start == destination:
            return [start.name]

        queue = deque([(start, [start])])
        visited = {start}

        while queue:
            page, path = queue.popleft()
            for neighbor in page.links.keys():
                if neighbor in visited:
                    continue
                next_path = path + [neighbor]
                if neighbor == destination:
                    return [p.name for p in next_path]
                visited.add(neighbor)
                queue.append((neighbor, next_path))

        return None

    def dry_run_workflow(self, steps: List[Dict[str, Any]], start_state: str = "page_main") -> Dict[str, Any]:
        """Runtime workflow lint against actual state machine instance bindings.

        Unlike static validation, this checks tools in `self.tools` (actual runtime
        registration), so it is the closest preflight before real execution.
        """
        states = {state.name: state for state in self.get_all_states()}
        current = self._resolve_state(states, start_state)
        if current is None:
            return {
                "success": False,
                "error": f"Unknown start_state: {start_state}",
                "steps": [],
            }

        results: List[Dict[str, Any]] = []
        for idx, step in enumerate(steps, start=1):
            target_name = step.get("state")
            tool_name = step.get("tool")
            target = self._resolve_state(states, target_name)

            if target is None:
                results.append({
                    "step": idx,
                    "tool": tool_name,
                    "target_state": target_name,
                    "from_state": current.name,
                    "reachable": False,
                    "path": None,
                    "error": f"Unknown target state: {target_name}",
                })
                return {"success": False, "error": "Workflow contains unknown state", "steps": results}

            path = self._find_path(current, target)
            tool_exists = self.get_tool(tool_name) is not None
            tool_available_in_target_state = tool_exists and self._tool_available_in_state(tool_name, target)
            reachable = path is not None and tool_available_in_target_state
            step_result = {
                "step": idx,
                "tool": tool_name,
                "target_state": target_name,
                "from_state": current.name,
                "reachable": reachable,
                "path": path,
                "tool_available_in_target_state": tool_available_in_target_state,
                "error": None,
            }
            if not tool_exists:
                step_result["error"] = f"Unknown tool: {tool_name}"
            elif not tool_available_in_target_state:
                step_result["error"] = f"Tool {tool_name} is not available in state {target_name}"
            elif path is None:
                step_result["error"] = f"No path from {current.name} to {target_name}"

            results.append(step_result)
            if not reachable:
                return {"success": False, "error": "Workflow contains unreachable step", "steps": results}

            current = target

        return {"success": True, "error": None, "steps": results}

    def run_daily_base_sweep(self, continue_on_failure: bool = False) -> Dict[str, Any]:
        """Execute the wrapped daily base sweep using existing handlers only.

        Sequence: mail -> dorm collect/feed -> commission -> research -> shop -> guild.
        This function performs validation first and reports detailed failure context.
        """
        expected_state = "page_main"
        dry_run = self.dry_run_workflow(self.DAILY_BASE_SWEEP_STEPS, start_state=self.get_current_state().name)
        if not dry_run["success"]:
            failure_analysis = self.analyze_workflow_failure_point(
                steps=self.DAILY_BASE_SWEEP_STEPS,
                start_state=self.get_current_state().name,
            )
            failure_point = failure_analysis.get("failure_point")
            failure_label = None if failure_point is None else (
                f"step={failure_point.get('step')} tool={failure_point.get('tool')} "
                f"target_state={failure_point.get('target_state')}"
            )
            return {
                "success": False,
                "data": {
                    "dry_run": dry_run,
                    "failure_analysis": failure_analysis,
                    "executed_steps": [],
                },
                "error": f"Daily base sweep validation failed: {dry_run['error']}" + (
                    "" if failure_label is None else f" ({failure_label})"
                ),
                "observed_state": self.get_current_state().name,
                "expected_state": expected_state,
            }

        executed_steps: List[Dict[str, Any]] = []
        failures: List[Dict[str, Any]] = []

        for step in self.DAILY_BASE_SWEEP_STEPS:
            target_state_name = step["state"]
            destination = Page.all_pages.get(target_state_name)
            if destination is None:
                step_result = {
                    "target_state": target_state_name,
                    "tool": step["tool"],
                    "success": False,
                    "error": f"KeyError: Page '{target_state_name}' not found in Page.all_pages",
                }
                failures.append(step_result)
                executed_steps.append(step_result)
                if not continue_on_failure:
                    break
                continue
            tool_name = step["tool"]
            arguments = dict(step.get("arguments", {}))

            step_result = {
                "target_state": target_state_name,
                "tool": tool_name,
                "success": True,
                "error": None,
            }
            try:
                self.transition(destination)
                self.call_tool(tool_name, **arguments)
            except Exception as exc:
                step_result["success"] = False
                step_result["error"] = f"{type(exc).__name__}: {exc}"
                failures.append(step_result)
                executed_steps.append(step_result)
                if not continue_on_failure:
                    break
            else:
                executed_steps.append(step_result)

        observed_state = self.get_current_state().name
        if not failures:
            self.transition(page_main)
            observed_state = self.get_current_state().name

        return {
            "success": len(failures) == 0,
            "data": {
                "dry_run": dry_run,
                "executed_steps": executed_steps,
                "failure_count": len(failures),
            },
            "error": None if not failures else f"{len(failures)} daily sweep step(s) failed",
            "observed_state": observed_state,
            "expected_state": expected_state,
        }

    @staticmethod
    def _build_tool_registry(tools_by_state: Dict[Page, List[Tool]]) -> Dict[str, Tool]:
        registry: Dict[str, Tool] = {}
        for tools in tools_by_state.values():
            for tool in tools:
                registry[tool.name] = tool
        return registry

    def get_available_tools(self, state: Optional[Page] = None) -> List[Tool]:
        """
        Returns a list of available tools for the given state.
        """
        if state is None:
            state = self.get_current_state()
        return self.tools.get(state, [])

    def get_all_tools(self) -> List[Tool]:
        return list(self.tool_registry.values())

    def get_tool(self, name: str) -> Optional[Tool]:
        return self.tool_registry.get(name)

    def call_tool(self, name: str, *args, **kwargs):
        tool = self.get_tool(name)
        if tool is None:
            raise KeyError(name)
        return tool(*args, **kwargs)
