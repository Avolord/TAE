"""
Enhanced Choice module to work with the SceneManager.
"""
from typing import Dict, Any, List, Union, Callable, Optional

from tae_engine.game_state import GameState
from tae_engine.conditions import Condition
from tae_engine.effects import Effect


class Choice:
    """Class representing a choice in the game."""
    
    def __init__(
        self, 
        text: str, 
        effect: Optional[Union[Dict, str, Effect, Callable, List]] = None,
        condition: Optional[Union[Dict, str, Condition, Callable]] = None,
        next_scene: Optional[str] = None,
        tags: Optional[List[str]] = None,
        description: Optional[str] = None
    ):
        """
        Initialize a choice.
        
        Args:
            text: The text of the choice shown to the player
            effect: Optional effect(s) to apply when the choice is made
            condition: Optional condition that determines if the choice is available
            next_scene: Optional ID of the scene to transition to after this choice
            tags: Optional list of tags for categorizing choices
            description: Optional description of what this choice represents
        """
        self.text = text
        self._effect = Effect.create(effect) if effect is not None else None
        self._condition = Condition.create(condition)
        self.next_scene = next_scene
        self.tags = tags or []
        self.description = description or ""
    
    def is_available(self, game_state: GameState) -> bool:
        """Check if this choice is available in the current game state."""
        return self._condition.check(game_state)
    
    def choose(self, scene_manager, action_description: Optional[str] = None) -> None:
        """
        Apply the effect of choosing this option and handle scene transition.
        
        This version works with the SceneManager to properly handle state history
        and scene transitions.
        
        Args:
            scene_manager: The SceneManager instance
            action_description: Optional description of the action
        """
        # Create a description if none provided
        if action_description is None:
            action_description = f"Chose: {self.text}"
        
        # Apply effect if there is one
        if self._effect:
            scene_manager.apply_effect(self._effect, action_description)
        
        # Handle scene transition if specified
        if self.next_scene:
            scene_manager.transition_to(self.next_scene, f"Transition after: {self.text}")
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Choice':
        """Create a Choice from a dictionary."""
        return cls(
            text=data["text"],
            effect=data.get("effect"),
            condition=data.get("condition"),
            next_scene=data.get("next_scene"),
            tags=data.get("tags"),
            description=data.get("description")
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
        """
        Initialize a choice set.
        
        Args:
            choices: List of choice data (can be various formats)
        """
        self.choices = [Choice.create(choice) for choice in choices]
    
    def get_available_choices(self, game_state: GameState) -> List[Choice]:
        """
        Get the subset of choices that are available in the current game state.
        
        Args:
            game_state: The current game state
            
        Returns:
            List of available choices
        """
        return [choice for choice in self.choices if choice.is_available(game_state)]
    
    def make_choice(self, choice_index: int, scene_manager) -> Optional[Choice]:
        """
        Make a choice by index from the available choices.
        
        Args:
            choice_index: The index of the choice in the available choices list
            scene_manager: The SceneManager instance
            
        Returns:
            The chosen Choice object, or None if the choice was invalid
            
        Note:
            This method first filters choices by availability, then selects by index.
        """
        available_choices = self.get_available_choices(scene_manager.game_state)
        
        if 0 <= choice_index < len(available_choices):
            choice = available_choices[choice_index]
            choice.choose(scene_manager)
            return choice
        
        return None
    
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
def choice_with_effect(text: str, effect_str: str, next_scene: Optional[str] = None) -> Choice:
    """
    Create a choice with an effect using shorthand notation.
    
    Args:
        text: The choice text
        effect_str: Effect in string notation (e.g., "add_item:Sword:1")
        next_scene: Optional ID of the scene to transition to
        
    Returns:
        A Choice object
    
    Examples:
        choice_with_effect("Pick up the sword", "add_item:Sword:1", "armory")
        choice_with_effect("Rest at the inn", "set_stat:health:100")
    """
    return Choice(text=text, effect=effect_str, next_scene=next_scene)


# Shorthand function for creating a choice with a condition
def choice_with_condition(text: str, condition_str: str, next_scene: Optional[str] = None) -> Choice:
    """
    Create a choice with a condition using shorthand notation.
    
    Args:
        text: The choice text
        condition_str: Condition in string notation (e.g., "has_item:Sword:1")
        next_scene: Optional ID of the scene to transition to
        
    Returns:
        A Choice object
    
    Examples:
        choice_with_condition("Use healing potion", "has_item:Healing Potion:1")
        choice_with_condition("Enter the cave", "check_stat:strength:>=:10", "cave_entrance")
    """
    return Choice(text=text, condition=condition_str, next_scene=next_scene)


# Shorthand function for creating a choice with both effect and condition
def choice_with_both(
    text: str, 
    condition_str: str, 
    effect_str: str,
    next_scene: Optional[str] = None
) -> Choice:
    """
    Create a choice with both a condition and an effect using shorthand notation.
    
    Args:
        text: The choice text
        condition_str: Condition in string notation
        effect_str: Effect in string notation
        next_scene: Optional ID of the scene to transition to
        
    Returns:
        A Choice object
    
    Examples:
        choice_with_both(
            "Use healing potion", 
            "has_item:Healing Potion:1",
            "add_stat:health:20",
            "camp_rest"
        )
    """
    return Choice(
        text=text, 
        condition=condition_str, 
        effect=effect_str, 
        next_scene=next_scene
    )