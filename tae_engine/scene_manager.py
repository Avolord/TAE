"""
Simplified scene management system for Text Adventure Engine.
Implements scene transitions and state history.
"""
from typing import Dict, Any, List, Callable, Optional, Union, Tuple
import copy

from tae_engine.game_state import GameState
from tae_engine.effects import Effect

class Scene:
    """
    A scene in the game.
    
    A scene represents a discrete section of gameplay with its own content,
    choices, and logic.
    """
    def __init__(
        self, 
        id: str, 
        handler: Callable,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a scene.
        
        Args:
            id: Unique identifier for the scene
            handler: Function that handles scene execution
            metadata: Optional metadata for the scene (tags, description, etc.)
        """
        self.id = id
        self.handler = handler
        self.metadata = metadata or {}
        
    def execute(self, scene_manager: 'SceneManager', *args, **kwargs) -> None:
        """
        Execute the scene's handler.
        
        Args:
            scene_manager: The SceneManager instance
            *args, **kwargs: Additional arguments to pass to the handler
        """
        self.handler(scene_manager, *args, **kwargs)


class StateHistoryEntry:
    """
    An entry in the state history.
    
    Contains a game state snapshot and metadata about the action that
    created this state.
    """
    def __init__(
        self, 
        game_state: GameState, 
        current_scene_id: str,
        action_description: Optional[str] = None
    ):
        """
        Initialize a state history entry.
        
        Args:
            game_state: The game state snapshot
            current_scene_id: The scene ID active when this state was created
            action_description: Optional description of the action that led to this state
        """
        self.game_state = copy.deepcopy(game_state)
        self.scene_id = current_scene_id
        self.description = action_description or "State change"


class SceneManager:
    """
    Manages scenes, transitions, and game state history.
    
    The SceneManager coordinates scene execution, handles transitions between scenes,
    and maintains a history of game states for undo operations.
    """
    def __init__(self, starting_scene_id: Optional[str] = None):
        """
        Initialize the scene manager.
        
        Args:
            starting_scene_id: Optional ID of the starting scene
        """
        self.scenes: Dict[str, Scene] = {}
        self.current_scene_id = starting_scene_id
        self.game_state = GameState()
        self.state_history: List[StateHistoryEntry] = []
        
        # Save initial state
        if starting_scene_id:
            self._save_state("Initial state")
    
    def register_scene(
        self, 
        scene_id: str, 
        handler: Callable,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Register a scene with the manager.
        
        Args:
            scene_id: Unique identifier for the scene
            handler: Function that handles scene execution
            metadata: Optional metadata for the scene
        """
        scene = Scene(scene_id, handler, metadata)
        self.scenes[scene_id] = scene
    
    def connect_scenes(self, from_scene_id: str, to_scene_id: str) -> None:
        """
        Legacy method kept for backward compatibility.
        Does nothing as explicit scene connections are no longer required.
        
        Args:
            from_scene_id: ID of the source scene
            to_scene_id: ID of the destination scene
        """
        pass  # No-op - explicit connections no longer needed
    
    def transition_to(
        self, 
        scene_id: str, 
        action_description: Optional[str] = None
    ) -> None:
        """
        Transition to a new scene.
        
        Args:
            scene_id: ID of the scene to transition to
            action_description: Optional description of the action causing the transition
            
        Raises:
            ValueError: If the scene doesn't exist
        """
        # Make sure the scene exists
        if scene_id not in self.scenes:
            raise ValueError(f"Scene '{scene_id}' not found")
            
        # Update current scene
        old_scene_id = self.current_scene_id
        self.current_scene_id = scene_id
        
        # Save state with transition info
        transition_description = action_description or f"Transition from {old_scene_id} to {scene_id}"
        self._save_state(transition_description)
    
    def apply_effect(
        self, 
        effect_data: Union[Dict, str, Effect, Callable, List],
        action_description: Optional[str] = None
    ) -> None:
        """
        Apply an effect and save the resulting state.
        
        This creates a new history entry after applying the effect.
        
        Args:
            effect_data: The effect to apply (can be any format supported by Effect.create)
            action_description: Optional description of the action
        """
        # Create the effect
        effect = Effect.create(effect_data)
        
        # Save state before applying effect
        self._save_state(f"Before: {action_description or 'Effect applied'}")
        
        # Apply the effect
        effect.apply(self.game_state)
        
        # Save state after applying effect
        self._save_state(action_description or "Effect applied")
    
    def run_current_scene(self, *args, **kwargs) -> None:
        """
        Execute the current scene.
        
        Args:
            *args, **kwargs: Additional arguments to pass to the scene handler
        
        Raises:
            ValueError: If there is no current scene
        """
        if self.current_scene_id is None:
            raise ValueError("No current scene to run")
            
        scene = self.scenes[self.current_scene_id]
        scene.execute(self, *args, **kwargs)
    
    def run_scene(self, scene_id: str, *args, **kwargs) -> None:
        """
        Transition to and execute a specific scene.
        
        Args:
            scene_id: ID of the scene to run
            *args, **kwargs: Additional arguments to pass to the scene handler
        """
        self.transition_to(scene_id, f"Transitioning to {scene_id}")
        self.run_current_scene(*args, **kwargs)
    
    def run_game(self, starting_scene_id: Optional[str] = None) -> None:
        """
        Run the game from a starting scene.
        
        This method will continue running scenes until there's no current scene.
        
        Args:
            starting_scene_id: Optional ID of the starting scene (overrides the current scene)
        """
        if starting_scene_id:
            self.transition_to(starting_scene_id, "Starting game")
        
        while self.current_scene_id:
            previous_scene = self.current_scene_id
            self.run_current_scene()
            
            # If scene didn't change the current scene, we're done
            if self.current_scene_id == previous_scene:
                break
    
    def back(self) -> bool:
        """
        Go back to the previous state by reverting to a previous entry in history.
        
        Returns:
            True if back operation was successful, False if no more history
        """
        # Need at least 2 entries to go back (current + previous)
        if len(self.state_history) < 2:
            return False
            
        # Remove current state
        self.state_history.pop()
        
        # Get the previous state
        previous_entry = self.state_history[-1]
        
        # Restore game state
        self.game_state = copy.deepcopy(previous_entry.game_state)
        self.current_scene_id = previous_entry.scene_id
        
        return True
    
    def get_state_history(self) -> List[Tuple[str, str]]:
        """
        Get a summary of the state history.
        
        Returns:
            List of (scene_id, description) tuples
        """
        return [(entry.scene_id, entry.description) for entry in self.state_history]
    
    def _save_state(self, description: str = "State change") -> None:
        """
        Save the current state to history.
        
        Args:
            description: Description of what caused this state change
        """
        entry = StateHistoryEntry(
            self.game_state, 
            self.current_scene_id,
            description
        )
        self.state_history.append(entry)