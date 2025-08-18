from module.ui.ui import UI
from module.ui.page import Page, page_dorm
from module.tool import Tool
from module.dorm.dorm import RewardDorm
from module.dorm.buy_furniture import BuyFurniture

class StateMachine:
    def __init__(self, ui: UI):
        """
        Initializes the StateMachine with a UI instance.

        Args:
            ui (UI): An instance of the UI class.
        """
        self.ui = ui
        self.tools = self._register_tools()

    def get_current_state(self) -> Page:
        """
        Returns the current state (page) of the bot.

        Returns:
            Page: The current page object.
        """
        return self.ui.ui_get_current_page()

    def get_possible_actions(self, state: Page = None) -> list[Page]:
        """
        Returns a list of possible next states from the given state.
        If no state is provided, it uses the current state.

        Args:
            state (Page, optional): The state to get actions for. Defaults to None.

        Returns:
            list[Page]: A list of possible destination pages.
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

    def get_all_states(self) -> list[Page]:
        """
        Returns a list of all possible states in the state machine.

        Returns:
            list[Page]: A list of all page objects.
        """
        return list(Page.all_pages.values())

    def _register_tools(self):
        """
        Registers all the tools for all the states.
        """
        dorm_handler = RewardDorm(self.ui.config, self.ui.device)
        buy_furniture_handler = BuyFurniture(self.ui.config, self.ui.device)

        return {
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
            ]
        }

    def get_available_tools(self, state: Page = None) -> list[Tool]:
        """
        Returns a list of available tools for the given state.
        """
        if state is None:
            state = self.get_current_state()
        return self.tools.get(state, [])
