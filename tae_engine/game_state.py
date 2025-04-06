from typing import Dict, Any, Union, List, Optional, Callable
import pickle
from datetime import datetime

class GameState:
    """Class to store and manage the game state."""
    
    def __init__(self):
        self.inventory: Dict[str, int] = {}
        self.stats: Dict[str, Any] = {}
        self.game_variables: Dict[str, Any] = {}
    
    def add_to_inventory(self, item_name: str, quantity: int = 1) -> None:
        """Add an item to the inventory."""
        if item_name in self.inventory:
            self.inventory[item_name] += quantity
        else:
            self.inventory[item_name] = quantity
    
    def remove_from_inventory(self, item_name: str, quantity: int = 1) -> bool:
        """Remove an item from the inventory."""
        if item_name not in self.inventory or self.inventory[item_name] < quantity:
            return False
        
        self.inventory[item_name] -= quantity
        if self.inventory[item_name] <= 0:
            del self.inventory[item_name]
        
        return True
    
    def update_stat(self, stat_name: str, value: Any) -> None:
        """Update a stat value."""
        self.stats[stat_name] = value
    
    def increment_stat(self, stat_name: str, amount: Union[int, float] = 1) -> None:
        """Increment a stat by the given amount."""
        if stat_name not in self.stats:
            self.stats[stat_name] = amount
        else:
            self.stats[stat_name] += amount

    def has_item(self, item_name: str, quantity: int = 1) -> bool:
        """Check if the player has at least the specified quantity of an item."""
        return item_name in self.inventory and self.inventory[item_name] >= quantity

    def check_stat(self, stat_name: str, value: Any, comparison: str = ">=") -> bool:
        """
        Check if a stat meets a certain condition.
        
        Args:
            stat_name: The name of the stat to check
            value: The value to compare against
            comparison: The comparison operator ("==", "!=", ">", "<", ">=", "<=")
            
        Returns:
            Whether the condition is met
        """
        if stat_name not in self.stats:
            return False
        
        current_value = self.stats[stat_name]
        
        if comparison == "==":
            return current_value == value
        elif comparison == "!=":
            return current_value != value
        elif comparison == ">":
            return current_value > value
        elif comparison == "<":
            return current_value < value
        elif comparison == ">=":
            return current_value >= value
        elif comparison == "<=":
            return current_value <= value
        else:
            raise ValueError(f"Unknown comparison operator: {comparison}")

    def set_variable(self, name: str, value: Any) -> None:
        """Set a game variable."""
        self.game_variables[name] = value
        
    def get_variable(self, name: str, default: Any = None) -> Any:
        """Get a game variable, returning default if it doesn't exist."""
        return self.game_variables.get(name, default)
    
    def to_dict(self) -> Dict[str, Any]:
        """Converts the game state to a JSON-serializable dictionary."""
        # Assuming inventory, stats, game_variables contain JSON-serializable types
        return {
            "inventory": self.inventory,
            "stats": self.stats,
            "game_variables": self.game_variables,
            # Add any other state variables here
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GameState':
        """Creates a GameState instance from a dictionary."""
        state = cls()
        state.inventory = data.get("inventory", {})
        state.stats = data.get("stats", {})
        state.game_variables = data.get("game_variables", {})
        # Load any other state variables here
        return state
