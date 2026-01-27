from typing import Any, Dict, List, Optional

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
        ]

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
            ]
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
