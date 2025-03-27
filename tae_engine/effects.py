from typing import Dict, Any, List, Union, Callable, Optional
from .game_state import GameState

class Effect:
    """Base class for effects that can be applied to the game state."""
    
    def apply(self, game_state: GameState) -> None:
        """Apply this effect to the game state."""
        pass
    
    @staticmethod
    def create(effect_data: Union[Dict, str, 'Effect', Callable, List]) -> 'Effect':
        """
        Factory method to create an effect from various formats.
        
        Args:
            effect_data: Can be one of:
                - Dict with effect type and parameters
                - String in shorthand notation (e.g., "add_item:Sword:1")
                - Effect instance
                - Callable that takes a GameState
                
        Returns:
            An Effect instance
        """
        if isinstance(effect_data, Effect):
            return effect_data
        
        if callable(effect_data):
            return FunctionEffect(effect_data)
        
        if isinstance(effect_data, str):
            # Parse shorthand notation
            parts = effect_data.split(":")
            effect_type = parts[0]
            
            if effect_type == "add_item":
                item_name = parts[1]
                quantity = int(parts[2]) if len(parts) > 2 else 1
                return AddItemEffect(item_name, quantity)
                
            elif effect_type == "remove_item":
                item_name = parts[1]
                quantity = int(parts[2]) if len(parts) > 2 else 1
                return RemoveItemEffect(item_name, quantity)
                
            elif effect_type == "set_stat":
                stat_name = parts[1]
                try:
                    # Try to parse as int or float
                    value = int(parts[2])
                except ValueError:
                    try:
                        value = float(parts[2])
                    except ValueError:
                        # If not a number, use as string
                        value = parts[2]
                return SetStatEffect(stat_name, value)
                
            elif effect_type == "add_stat":
                stat_name = parts[1]
                value = float(parts[2]) if '.' in parts[2] else int(parts[2])
                return AddStatEffect(stat_name, value)
                
            elif effect_type == "set_var":
                var_name = parts[1]
                try:
                    # Try to parse as int or float
                    value = int(parts[2])
                except ValueError:
                    try:
                        value = float(parts[2])
                    except ValueError:
                        # If not a number, use as string
                        value = parts[2]
                return SetVarEffect(var_name, value)
                
            else:
                raise ValueError(f"Unknown effect type: {effect_type}")
        
        if isinstance(effect_data, dict):
            effect_type = effect_data.get("type")
            
            if effect_type == "add_item":
                return AddItemEffect(
                    effect_data["item"],
                    effect_data.get("quantity", 1)
                )
                
            elif effect_type == "remove_item":
                return RemoveItemEffect(
                    effect_data["item"],
                    effect_data.get("quantity", 1)
                )
                
            elif effect_type == "set_stat":
                return SetStatEffect(
                    effect_data["stat"],
                    effect_data["value"]
                )
                
            elif effect_type == "add_stat":
                return AddStatEffect(
                    effect_data["stat"],
                    effect_data["value"]
                )
                
            elif effect_type == "set_var":
                return SetVarEffect(
                    effect_data["var"],
                    effect_data["value"]
                )
                
            elif effect_type == "compound":
                return CompoundEffect([
                    Effect.create(sub_effect) for sub_effect in effect_data["effects"]
                ])
                
            else:
                raise ValueError(f"Unknown effect type: {effect_type}")
        
        if isinstance(effect_data, List):
            return CompoundEffect([
                Effect.create(sub_effect) for sub_effect in effect_data
            ])
        
        raise ValueError(f"Cannot create effect from: {effect_data}")


class AddItemEffect(Effect):
    """Effect that adds an item to the inventory."""
    
    def __init__(self, item: str, quantity: int = 1):
        self.item = item
        self.quantity = quantity
    
    def apply(self, game_state: GameState) -> None:
        game_state.add_to_inventory(self.item, self.quantity)


class RemoveItemEffect(Effect):
    """Effect that removes an item from the inventory."""
    
    def __init__(self, item: str, quantity: int = 1):
        self.item = item
        self.quantity = quantity
    
    def apply(self, game_state: GameState) -> None:
        game_state.remove_from_inventory(self.item, self.quantity)


class SetStatEffect(Effect):
    """Effect that sets a stat to a value."""
    
    def __init__(self, stat: str, value: Any):
        self.stat = stat
        self.value = value
    
    def apply(self, game_state: GameState) -> None:
        game_state.update_stat(self.stat, self.value)


class AddStatEffect(Effect):
    """Effect that adds a value to a stat."""
    
    def __init__(self, stat: str, value: Union[int, float]):
        self.stat = stat
        self.value = value
    
    def apply(self, game_state: GameState) -> None:
        game_state.increment_stat(self.stat, self.value)


class SetVarEffect(Effect):
    """Effect that sets a game variable."""
    
    def __init__(self, var: str, value: Any):
        self.var = var
        self.value = value
    
    def apply(self, game_state: GameState) -> None:
        game_state.set_variable(self.var, self.value)


class CompoundEffect(Effect):
    """Effect that applies multiple effects."""
    
    def __init__(self, effects: List[Effect]):
        self.effects = effects
    
    def apply(self, game_state: GameState) -> None:
        for effect in self.effects:
            effect.apply(game_state)


class FunctionEffect(Effect):
    """Effect that applies a custom function to the game state."""
    
    def __init__(self, func: Callable[[GameState], None]):
        self.func = func
    
    def apply(self, game_state: GameState) -> None:
        self.func(game_state)