# Exploration Log - ALAS Project

## 2026-01-26: Porting Functional Core and Implementing Vision Tools

### Actions Taken
1. **Branch Created**: Switched to new branch `dev/port-alas-functional` to safely modify the `ALAS` project.
2. **Core Porting**: Mirrored the verified functional ALAS core from `C:\_projects\ALASGetFunctional\Alas-with-Dashboard` into `C:\_projects\ALAS\alas_wrapped`.
    - Included all `assets`, `module` logic, and `config` files.
    - Excluded `.git` and the new `tools/` directory to preserve orchestration structure.
3. **Phase 0 Verification**: Confirmed that `alas_wrapped.tools.navigation` is importable and functional.
    - Successfully executed `get_current_page()` which connected to the running emulator and identified `page_main`.
4. **Phase 0.5 Tooling (Vision)**: Created `alas_wrapped/tools/vision.py` to provide granular perception tools for the LLM.
    - `list_assets(filter)`: Searches the `assets/` directory for template names.
    - `match_asset(name)`: Uses ALAS's internal template matching to find objects on screen and return coordinates/similarity.
    - `click_asset(name)`: A safer alternative to raw coordinate clicking; finds the image and taps it.
5. **Vision Verification**: Verified `vision.list_assets` correctly finds assets in the `cn/` folder (normalized from `zh-CN` config).

### Findings
- **Deterministic vs. Vision**: Confirmed that while ALAS is great at "Macros" (`goto`), the LLM needs "Micro" vision tools (`match_asset`) to handle system-level obstacles like MEmu launcher ads that ALAS's internal state machine doesn't know about.
- **Bug Identified**: `navigation.get_current_page()` failed with `AttributeError: 'ToolContext' object has no attribute 'interval_timer'` when the screen was in an unknown state. This needs to be fixed in `tools/_context.py` to ensure robust error reporting.

### Next Steps
- [ ] Fix `interval_timer` attribute in `ToolContext`.
- [ ] Implement `alas.diagnose_state()` tool to dump all matched templates when in an "Unknown" state.
- [ ] Begin Phase I: Wrap these Python tools in the `agent_orchestrator/alas_mcp_server.py`.
