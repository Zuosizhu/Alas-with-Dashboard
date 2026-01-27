"""
Shared context for ALAS tools.

Provides lazy initialization of Device and UI components
without running the full AzurLaneAutoScript.
"""

from typing import Optional

from cached_property import cached_property

from module.config.config import AzurLaneConfig
from module.device.device import Device
from module.ui.ui import UI


class ToolContext(UI):
    """
    Minimal context for running ALAS tools.

    Inherits from UI to get navigation methods (ui_goto, ui_get_current_page).
    Lazily initializes Device and Config on first use.
    """

    def __init__(self, config_name: str = "alas"):
        """
        Args:
            config_name: Name of the config to load (default: "alas")
        """
        super().__init__(config=config_name)
        self.config_name = config_name
        self._config: Optional[AzurLaneConfig] = None
        self._device: Optional[Device] = None

    @cached_property
    def config(self) -> AzurLaneConfig:
        """Lazily load config on first access."""
        return AzurLaneConfig(config_name=self.config_name)

    @cached_property
    def device(self) -> Device:
        """Lazily initialize device on first access."""
        return Device(config=self.config)


# Global singleton - initialized on first tool call
_context: Optional[ToolContext] = None


def get_context(config_name: str = "alas") -> ToolContext:
    """
    Get or create the global tool context.

    Args:
        config_name: Name of config to use (only used on first call)

    Returns:
        ToolContext: The shared context instance
    """
    global _context
    if _context is None:
        _context = ToolContext(config_name=config_name)
    return _context


def reset_context():
    """Reset the global context. Useful for testing."""
    global _context
    _context = None
