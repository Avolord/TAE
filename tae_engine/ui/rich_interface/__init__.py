"""
Rich-based UI components for text adventure games.
"""

from tae_engine.game_state import GameState
from tae_engine.ui.rich_interface.base_ui import BaseUI
from tae_engine.ui.rich_interface.choice_box import ChoiceBox
from tae_engine.ui.rich_interface.dialogue_box import DialogueBox
from tae_engine.ui.rich_interface.shop_ui import ShopUI
from tae_engine.ui.rich_interface.stats_panel import StatsPanel
from tae_engine.ui.rich_interface.inventory_ui import InventoryUI

__all__ = [
    'BaseUI',
    'ChoiceBox',
    'DialogueBox',
    'ShopUI',
    'StatsPanel',
    'InventoryUI',
]