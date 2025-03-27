from typing import Dict, Any, List, Union, Callable, Optional
from .game_state import GameState
from .conditions import Condition
from .effects import Effect

class Choice:
    """Class representing a choice in the game."""
    
    def __init__(
        self, 
        text: str, 
        effect: Optional[Union[Dict, str, Effect, Callable]] = None,
        condition: Optional[Union[Dict, str, Condition, Callable]] = None,
        next_scene: Optional[str] = None,
        tags: Optional[List[str]] = None
    ):
        self.text = text
        self._effect = Effect.create(effect) if effect is not None else None
        self._condition = Condition.create(condition)
        self.next_scene = next_scene
        self.tags = tags or []
    
    def is_available(self, game_state: GameState) -> bool:
        """Check if this choice is available in the current game state."""
        return self._condition.check(game_state)
    
    def choose(self, game_state: GameState) -> None:
        """Apply the effect of choosing this option."""
        if self._effect:
            self._effect.apply(game_state)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Choice':
        """Create a Choice from a dictionary."""
        return cls(
            text=data["text"],
            effect=data.get("effect"),
            condition=data.get("condition"),
            next_scene=data.get("next_scene"),
            tags=data.get("tags")
        )
    
    @classmethod
    def from_string(cls, text: str) -> 'Choice':
        """
        Create a simple Choice from a string.
        
        This is a shorthand for creating choices without effects or conditions.
        """
        return cls(text=text)
    
    @classmethod
    def create(cls, data: Union[Dict, str, 'Choice']) -> 'Choice':
        """
        Factory method to create a Choice from various formats.
        
        Args:
            data: Can be one of:
                - Dict with choice parameters
                - String (just the choice text)
                - Choice instance
                
        Returns:
            A Choice instance
        """
        if isinstance(data, Choice):
            return data
        
        if isinstance(data, str):
            return cls.from_string(data)
        
        if isinstance(data, dict):
            return cls.from_dict(data)
        
        raise ValueError(f"Cannot create Choice from: {data}")


class ChoiceSet:
    """A set of choices for the player to choose from."""
    
    def __init__(self, choices: List[Union[Dict, str, Choice]]):
        self.choices = [Choice.create(choice) for choice in choices]
    
    def get_available_choices(self, game_state: GameState) -> List[Choice]:
        """Get the subset of choices that are available in the current game state."""
        return [choice for choice in self.choices if choice.is_available(game_state)]
    
    @classmethod
    def create(cls, data: Union[List, Dict, 'ChoiceSet']) -> 'ChoiceSet':
        """
        Factory method to create a ChoiceSet from various formats.
        
        Args:
            data: Can be one of:
                - List of Choice data (dicts, strings, or Choice objects)
                - Dict with a 'choices' key
                - ChoiceSet instance
                
        Returns:
            A ChoiceSet instance
        """
        if isinstance(data, ChoiceSet):
            return data
        
        if isinstance(data, list):
            return cls(data)
        
        if isinstance(data, dict) and "choices" in data:
            return cls(data["choices"])
        
        raise ValueError(f"Cannot create ChoiceSet from: {data}")


# Shorthand function for creating a choice with an effect
def choice_with_effect(text: str, effect_str: str) -> Choice:
    """
    Create a choice with an effect using shorthand notation.
    
    Examples:
        choice_with_effect("Pick up the sword", "add_item:Sword:1")
        choice_with_effect("Rest at the inn", "set_stat:health:100")
    """
    return Choice(text=text, effect=effect_str)


# Shorthand function for creating a choice with a condition
def choice_with_condition(text: str, condition_str: str) -> Choice:
    """
    Create a choice with a condition using shorthand notation.
    
    Examples:
        choice_with_condition("Use healing potion", "has_item:Healing Potion:1")
        choice_with_condition("Enter the cave", "check_stat:strength:>=:10")
    """
    return Choice(text=text, condition=condition_str)


# Shorthand function for creating a choice with both effect and condition
def choice_with_both(text: str, condition_str: str, effect_str: str) -> Choice:
    """
    Create a choice with both a condition and an effect using shorthand notation.
    
    Examples:
        choice_with_both(
            "Use healing potion", 
            "has_item:Healing Potion:1",
            "add_stat:health:20"
        )
    """
    return Choice(text=text, condition=condition_str, effect=effect_str)