"""
Text Adventure Engine (TAE) - A framework for creating text adventure games.
"""

from tae_engine.game_state import GameState
from tae_engine.effects import Effect
from tae_engine.conditions import Condition
from tae_engine.choice import Choice, ChoiceSet, choice_with_effect, choice_with_condition, choice_with_both

__all__ = [
    'GameState',
    'Effect',
    'Condition',
    'Choice',
    'ChoiceSet',
    'choice_with_effect',
    'choice_with_condition', 
    'choice_with_both'
]