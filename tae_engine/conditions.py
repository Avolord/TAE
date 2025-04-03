from typing import Dict, Any, List, Union, Callable, Optional
from tae_engine.game_state import GameState

class Condition:
    """Base class for conditions that can be checked against the game state."""
    
    def check(self, game_state: GameState) -> bool:
        """Check if this condition is met by the game state."""
        return True
    
    @staticmethod
    def create(condition_data: Union[Dict, str, 'Condition', Callable, None]) -> 'Condition':
        """
        Factory method to create a condition from various formats.
        
        Args:
            condition_data: Can be one of:
                - Dict with condition type and parameters
                - String in shorthand notation (e.g., "has_item:Sword:1")
                - Condition instance
                - Callable that takes a GameState and returns bool
                - None (which creates an AlwaysTrueCondition)
                
        Returns:
            A Condition instance
        """
        if condition_data is None:
            return AlwaysTrueCondition()
        
        if isinstance(condition_data, Condition):
            return condition_data
        
        if callable(condition_data):
            return FunctionCondition(condition_data)
        
        if isinstance(condition_data, str):
            # Parse shorthand notation
            parts = condition_data.split(":")
            condition_type = parts[0]
            
            if condition_type == "has_item":
                item_name = parts[1]
                quantity = int(parts[2]) if len(parts) > 2 else 1
                return HasItemCondition(item_name, quantity)
                
            elif condition_type == "check_stat":
                stat_name = parts[1]
                comparison = parts[2] if len(parts) > 3 else "=="
                
                try:
                    # Try to parse as int
                    value = int(parts[3] if len(parts) > 3 else parts[2])
                except ValueError:
                    try:
                        # Try to parse as float
                        value = float(parts[3] if len(parts) > 3 else parts[2])
                    except ValueError:
                        # Use as string
                        value = parts[3] if len(parts) > 3 else parts[2]
                
                return CheckStatCondition(stat_name, value, comparison)
                
            elif condition_type == "check_var":
                var_name = parts[1]
                comparison = parts[2] if len(parts) > 3 else "=="
                
                try:
                    # Try to parse as int
                    value = int(parts[3] if len(parts) > 3 else parts[2])
                except ValueError:
                    try:
                        # Try to parse as float
                        value = float(parts[3] if len(parts) > 3 else parts[2])
                    except ValueError:
                        # Use as string
                        value = parts[3] if len(parts) > 3 else parts[2]
                
                return CheckVarCondition(var_name, value, comparison)
                
            else:
                raise ValueError(f"Unknown condition type: {condition_type}")
        
        if isinstance(condition_data, dict):
            condition_type = condition_data.get("type")
            
            if condition_type == "has_item":
                return HasItemCondition(
                    condition_data["item"],
                    condition_data.get("quantity", 1)
                )
                
            elif condition_type == "check_stat":
                return CheckStatCondition(
                    condition_data["stat"],
                    condition_data["value"],
                    condition_data.get("comparison", "==")
                )
                
            elif condition_type == "check_var":
                return CheckVarCondition(
                    condition_data["var"],
                    condition_data["value"],
                    condition_data.get("comparison", "==")
                )
                
            elif condition_type == "and":
                return AndCondition([
                    Condition.create(sub_cond) for sub_cond in condition_data["conditions"]
                ])
                
            elif condition_type == "or":
                return OrCondition([
                    Condition.create(sub_cond) for sub_cond in condition_data["conditions"]
                ])
                
            elif condition_type == "not":
                return NotCondition(
                    Condition.create(condition_data["condition"])
                )
                
            else:
                raise ValueError(f"Unknown condition type: {condition_type}")
        
        raise ValueError(f"Cannot create condition from: {condition_data}")


class AlwaysTrueCondition(Condition):
    """Condition that always evaluates to True."""
    
    def check(self, game_state: GameState) -> bool:
        return True


class HasItemCondition(Condition):
    """Condition that checks if the player has an item."""
    
    def __init__(self, item: str, quantity: int = 1):
        self.item = item
        self.quantity = quantity
    
    def check(self, game_state: GameState) -> bool:
        return game_state.has_item(self.item, self.quantity)


class CheckStatCondition(Condition):
    """Condition that checks if a stat meets a criterion."""
    
    def __init__(self, stat: str, value: Any, comparison: str = "=="):
        self.stat = stat
        self.value = value
        self.comparison = comparison
    
    def check(self, game_state: GameState) -> bool:
        return game_state.check_stat(self.stat, self.value, self.comparison)


class CheckVarCondition(Condition):
    """Condition that checks if a game variable meets a criterion."""
    
    def __init__(self, var: str, value: Any, comparison: str = "=="):
        self.var = var
        self.value = value
        self.comparison = comparison
    
    def check(self, game_state: GameState) -> bool:
        current_value = game_state.get_variable(self.var)
        
        if current_value is None:
            return False
        
        if self.comparison == "==":
            return current_value == self.value
        elif self.comparison == "!=":
            return current_value != self.value
        elif self.comparison == ">":
            return current_value > self.value
        elif self.comparison == "<":
            return current_value < self.value
        elif self.comparison == ">=":
            return current_value >= self.value
        elif self.comparison == "<=":
            return current_value <= self.value
        else:
            raise ValueError(f"Unknown comparison operator: {self.comparison}")


class AndCondition(Condition):
    """Condition that checks if all subconditions are met."""
    
    def __init__(self, conditions: List[Condition]):
        self.conditions = conditions
    
    def check(self, game_state: GameState) -> bool:
        return all(cond.check(game_state) for cond in self.conditions)


class OrCondition(Condition):
    """Condition that checks if any subcondition is met."""
    
    def __init__(self, conditions: List[Condition]):
        self.conditions = conditions
    
    def check(self, game_state: GameState) -> bool:
        return any(cond.check(game_state) for cond in self.conditions)


class NotCondition(Condition):
    """Condition that negates another condition."""
    
    def __init__(self, condition: Condition):
        self.condition = condition
    
    def check(self, game_state: GameState) -> bool:
        return not self.condition.check(game_state)


class FunctionCondition(Condition):
    """Condition that uses a custom function to check the game state."""
    
    def __init__(self, func: Callable[[GameState], bool]):
        self.func = func
    
    def check(self, game_state: GameState) -> bool:
        return self.func(game_state)