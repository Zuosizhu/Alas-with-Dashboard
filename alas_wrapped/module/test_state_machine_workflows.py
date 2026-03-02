import sys
import types

# Test-only stub so importing state_machine does not require system libGL for cv2.
if "cv2" not in sys.modules:
    sys.modules["cv2"] = types.ModuleType("cv2")

from module.state_machine import StateMachine
from module.tool import Tool

# These tests intentionally use FakePage/FakeUI to isolate state-machine logic.
# They validate harness/graph rules, not OCR/device runtime behavior.

class FakePage:
    def __init__(self, name: str):
        self.name = name
        self.links = {}

    def connect(self, *others):
        for other in others:
            self.links[other] = None


class FakeUI:
    def __init__(self, start_page):
        self._current = start_page
        self.transitions = []
        self.config = object()
        self.device = object()

    def ui_get_current_page(self):
        return self._current

    def ui_goto(self, destination):
        self.transitions.append((self._current.name, destination.name))
        self._current = destination


class _StateMachineHarness(StateMachine):
    def __init__(self, ui, tools_by_state, states):
        self._tools_by_state = tools_by_state
        self._states = states
        super().__init__(ui)

    def _register_tools(self):
        return self._tools_by_state

    def get_all_states(self):
        return self._states


def build_pages():
    main = FakePage("page_main")
    dorm = FakePage("page_dorm")
    commission = FakePage("page_commission")
    research = FakePage("page_research")
    shop = FakePage("page_shop")
    guild = FakePage("page_guild")

    main.connect(dorm, commission, research, shop, guild)
    dorm.connect(main, commission, research, shop, guild)
    commission.connect(main, dorm, research, shop, guild)
    research.connect(main, dorm, commission, shop, guild)
    shop.connect(main, dorm, commission, research, guild)
    guild.connect(main, dorm, commission, research, shop)

    return [main, dorm, commission, research, shop, guild]


def build_tools_by_state(pages, events):
    by_name = {p.name: p for p in pages}

    def marker(name):
        def run(*_args, **_kwargs):
            events.append(name)
        return run

    return {
        by_name["page_main"]: [
            Tool("main.collect_mail", "mail", marker("main.collect_mail")),
        ],
        by_name["page_dorm"]: [
            Tool("dorm.collect_rewards", "dorm collect", marker("dorm.collect_rewards")),
            Tool("dorm.feed_ships", "dorm feed", marker("dorm.feed_ships")),
        ],
        by_name["page_commission"]: [
            Tool("commission.run", "commission", marker("commission.run")),
        ],
        by_name["page_research"]: [
            Tool("research.run", "research", marker("research.run")),
        ],
        by_name["page_shop"]: [
            Tool("shop.run", "shop", marker("shop.run")),
        ],
        by_name["page_guild"]: [
            Tool("guild.collect_lobby_rewards", "guild", marker("guild.collect_lobby_rewards")),
        ],
    }


def test_daily_base_sweep_dry_run_success(monkeypatch):
    pages = build_pages()
    events = []
    tools = build_tools_by_state(pages, events)
    ui = FakeUI(pages[0])

    sm = _StateMachineHarness(ui, tools, pages)
    sm.tool_registry["workflow.daily_base_sweep"] = Tool("workflow.daily_base_sweep", "workflow", sm.run_daily_base_sweep)

    dry = sm.dry_run_workflow(StateMachine.DAILY_BASE_SWEEP_STEPS, start_state="page_main")
    assert dry["success"] is True
    assert len(dry["steps"]) == len(StateMachine.DAILY_BASE_SWEEP_STEPS)


def test_daily_base_sweep_executes_all_steps_and_returns_main(monkeypatch):
    pages = build_pages()
    events = []
    tools = build_tools_by_state(pages, events)
    ui = FakeUI(pages[1])  # start from dorm to prove cross-state transition

    sm = _StateMachineHarness(ui, tools, pages)
    sm.tool_registry["workflow.daily_base_sweep"] = Tool("workflow.daily_base_sweep", "workflow", sm.run_daily_base_sweep)

    import module.state_machine as sm_module
    monkeypatch.setattr(sm_module.Page, "all_pages", {p.name: p for p in pages}, raising=False)
    monkeypatch.setattr(sm_module, "page_main", pages[0], raising=False)

    result = sm.run_daily_base_sweep()

    assert result["success"] is True
    assert result["observed_state"] == "page_main"
    assert events == [
        "main.collect_mail",
        "dorm.collect_rewards",
        "dorm.feed_ships",
        "commission.run",
        "research.run",
        "shop.run",
        "guild.collect_lobby_rewards",
    ]


def test_dry_run_reports_unreachable_step():
    main = FakePage("page_main")
    dorm = FakePage("page_dorm")
    # no link from main -> dorm
    dorm.connect(main)
    pages = [main, dorm]
    events = []

    tools = {
        main: [Tool("main.collect_mail", "mail", lambda: events.append("mail"))],
        dorm: [Tool("dorm.collect_rewards", "dorm", lambda: events.append("dorm"))],
    }

    sm = _StateMachineHarness(FakeUI(main), tools, pages)
    dry = sm.dry_run_workflow(
        [
            {"state": "page_main", "tool": "main.collect_mail", "arguments": {}},
            {"state": "page_dorm", "tool": "dorm.collect_rewards", "arguments": {}},
        ],
        start_state="page_main",
    )

    assert dry["success"] is False
    assert dry["steps"][1]["reachable"] is False
    assert "No path" in dry["steps"][1]["error"]


def test_dry_run_reports_tool_not_available_on_target_state():
    main = FakePage("page_main")
    dorm = FakePage("page_dorm")
    main.connect(dorm)
    dorm.connect(main)
    pages = [main, dorm]

    tools = {
        main: [Tool("main.collect_mail", "mail", lambda: None)],
        dorm: [],
    }

    sm = _StateMachineHarness(FakeUI(main), tools, pages)
    dry = sm.dry_run_workflow(
        [
            {"state": "page_dorm", "tool": "main.collect_mail", "arguments": {}},
        ],
        start_state="page_main",
    )

    assert dry["success"] is False
    assert dry["steps"][0]["tool_available_in_target_state"] is False
    assert "not available" in dry["steps"][0]["error"]


def test_analyze_workflow_failure_point_returns_first_failure_detail():
    main = FakePage("page_main")
    dorm = FakePage("page_dorm")
    main.connect(dorm)
    pages = [main, dorm]

    tools = {
        main: [Tool("main.collect_mail", "mail", lambda: None)],
        dorm: [Tool("dorm.collect_rewards", "dorm", lambda: None)],
    }

    sm = _StateMachineHarness(FakeUI(main), tools, pages)
    analysis = sm.analyze_workflow_failure_point(
        [
            {"state": "page_main", "tool": "main.collect_mail", "arguments": {}},
            {"state": "page_dorm", "tool": "dorm.collect_rewards", "arguments": {}},
            {"state": "page_main", "tool": "dorm.collect_rewards", "arguments": {}},
        ],
        start_state="page_main",
    )

    assert analysis["success"] is False
    assert analysis["failure_point"]["step"] == 3
    assert analysis["failure_point"]["tool"] == "dorm.collect_rewards"


def test_semantic_spec_validator_accepts_daily_base_sweep(monkeypatch):
    pages = build_pages()
    import module.state_machine as sm_module
    monkeypatch.setattr(sm_module.Page, "all_pages", {p.name: p for p in pages}, raising=False)

    result = StateMachine.validate_workflow_spec_against_graph(
        steps=StateMachine.DAILY_BASE_SWEEP_STEPS,
        start_state="page_main",
    )

    assert result["success"] is True
    assert len(result["steps"]) == len(StateMachine.DAILY_BASE_SWEEP_STEPS)


def test_semantic_spec_validator_detects_tool_state_mismatch(monkeypatch):
    pages = build_pages()
    import module.state_machine as sm_module
    monkeypatch.setattr(sm_module.Page, "all_pages", {p.name: p for p in pages}, raising=False)

    bad_steps = [
        {"state": "page_dorm", "tool": "main.collect_mail", "arguments": {}},
    ]
    result = StateMachine.validate_workflow_spec_against_graph(
        steps=bad_steps,
        start_state="page_main",
    )

    assert result["success"] is False
    assert result["error"] == "Workflow contains tool/state mismatch"
