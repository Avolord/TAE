"""
Demo showing how to use the simplified SceneManager with updated UI components.
"""
from rich.console import Console

from tae_engine.game_state import GameState
from tae_engine.choice import Choice, ChoiceSet
from tae_engine.ui.rich_interface.base_ui import BaseUI
from tae_engine.ui.rich_interface.choice_box import ChoiceBox
from tae_engine.ui.rich_interface.dialogue_box import DialogueBox
from tae_engine.ui.rich_interface.inventory_ui import InventoryUI
from tae_engine.scene_manager import SceneManager


def main():
    """Main entry point for the demo."""
    # Initialize the console and scene manager
    console = Console()
    scene_manager = SceneManager()
    
    # Initialize the game state with some starting values
    scene_manager.game_state.update_stat("health", 100)
    scene_manager.game_state.update_stat("gold", 50)
    scene_manager.game_state.add_to_inventory("Rusty Sword", 1)
    
    # Register scenes
    scene_manager.register_scene("start", scene_start)
    scene_manager.register_scene("forest", scene_forest)
    scene_manager.register_scene("forest_treasure", scene_forest_treasure)
    scene_manager.register_scene("inventory", scene_inventory)
    scene_manager.register_scene("end", scene_end)
    
    # Start the game
    scene_manager.run_game("start")


def scene_start(scene_manager, **kwargs):
    """Starting scene with dialogue and choices."""
    # Create UI components with the shared console
    console = Console()
    dialogue_ui = DialogueBox(console)
    dialogue_ui.game_state = scene_manager.game_state
    
    choice_ui = ChoiceBox(console)
    choice_ui.game_state = scene_manager.game_state
    
    # Show dialogue with scene_manager for the back action
    dialogue_ui.show(
        "Guide", 
        [
            "Welcome, adventurer! You find yourself at the edge of a mysterious forest.",
            "Be careful - dangers lurk within the trees. But so do treasures!",
            "What would you like to do?"
        ],
        "The Adventure Begins",
        scene_manager=scene_manager
    )
    
    # Define choices
    choices = ChoiceSet([
        Choice(
            text="Enter the forest", 
            next_scene="forest"
        ),
        Choice(
            text="Check my inventory first",
            next_scene="inventory"
        ),
        Choice(
            text="Rest to recover health",
            effect="set_stat:health:100", 
            next_scene="start"
        ),
        # This choice requires having at least 100 gold
        Choice(
            text="Buy a better sword (100 gold)",
            condition="check_stat:gold:>=:100", 
            effect=[
                "add_stat:gold:-100",
                "add_item:Steel Sword:1"
            ],
            next_scene="start"
        )
    ])
    
    # Show choices
    choice_ui.show("Forest Edge", choices, scene_manager, "What will you do?")


def scene_forest(scene_manager, **kwargs):
    """Forest scene with encounter."""
    console = Console()
    dialogue_ui = DialogueBox(console)
    dialogue_ui.game_state = scene_manager.game_state
    
    choice_ui = ChoiceBox(console)
    choice_ui.game_state = scene_manager.game_state
    
    # Show description
    dialogue_ui.show(
        "Narrator", 
        [
            "You venture into the dense forest. The canopy above blocks most of the sunlight.",
            "As you walk deeper, you hear rustling in the bushes ahead..."
        ],
        "The Dark Forest",
        scene_manager=scene_manager
    )
    
    # Create a choice set with a combat encounter
    choices = ChoiceSet([
        Choice(
            text="Attack with your weapon", 
            effect="add_stat:health:-10",  # You get hurt a bit
            next_scene="forest_treasure"
        ),
        Choice(
            text="Use Steel Sword for powerful attack",
            condition="has_item:Steel Sword:1",
            next_scene="forest_treasure"
        ),
        Choice(
            text="Try to sneak past",
            condition="check_stat:health:>:50",  # Need to be healthy to sneak
            next_scene="forest_treasure"
        ),
        Choice(
            text="Run back to the forest edge",
            next_scene="start"
        )
    ])
    
    choice_ui.show("Forest Encounter", choices, scene_manager, "A goblin jumps out!")


def scene_forest_treasure(scene_manager, **kwargs):
    """Finding treasure after the encounter."""
    console = Console()
    dialogue_ui = DialogueBox(console)
    dialogue_ui.game_state = scene_manager.game_state
    
    # Show treasure discovery
    dialogue_ui.show(
        "Narrator", 
        [
            "You defeated the goblin! Behind where it was hiding, you find a small chest.",
            "Inside is a potion and 50 gold coins."
        ],
        "Victory!",
        scene_manager=scene_manager
    )
    
    # Apply effects for finding treasure
    scene_manager.apply_effect("add_item:Health Potion:1", "Found a healing potion")
    scene_manager.apply_effect("add_stat:gold:50", "Found 50 gold coins")
    
    # Transition to end scene
    scene_manager.transition_to("end", "Completed forest adventure")


def scene_inventory(scene_manager, **kwargs):
    """Display the player's inventory."""
    console = Console()
    inventory_ui = InventoryUI(console)
    inventory_ui.game_state = scene_manager.game_state
    
    inventory_ui.show("Player", "Check your gear", scene_manager=scene_manager)
    
    # Return to start scene
    scene_manager.transition_to("start", "Finished checking inventory")


def scene_end(scene_manager, **kwargs):
    """End scene with final dialogue."""
    console = Console()
    dialogue_ui = DialogueBox(console)
    dialogue_ui.game_state = scene_manager.game_state
    
    dialogue_ui.show(
        "Narrator", 
        [
            "With the goblin defeated and treasure in hand, you decide to return to town.",
            "This adventure has come to an end, but many more await in the future!",
            "THE END"
        ],
        "Adventure Complete",
        scene_manager=scene_manager
    )
    
    # End the game by setting current_scene to None
    scene_manager.current_scene_id = None


if __name__ == "__main__":
    main()