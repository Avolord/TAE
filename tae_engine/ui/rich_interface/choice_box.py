from typing import List, Union, Optional
from rich.panel import Panel
from rich.box import ROUNDED

from tae_engine.ui.rich_interface.base_ui import BaseUI
from tae_engine.choice import Choice, ChoiceSet


class ChoiceBox(BaseUI):
    """UI component for displaying choices."""
    
    def show(
        self, 
        title: str, 
        choices: Union[List[Union[str, Choice]], ChoiceSet], 
        scene_manager = None,
        header_subtitle: Optional[str] = None
    ) -> Optional[Choice]:
        """
        Display a set of choices to the user.
        
        Args:
            title: The title of the choice box
            choices: Either a ChoiceSet or a list of Choice objects/strings/dicts
            scene_manager: The SceneManager instance
            header_subtitle: Optional subtitle for the header
            
        Returns:
            The selected Choice object or None if no valid choice was made
        """
        # Set scene_manager for back action
        self.scene_manager = scene_manager
        
        # Convert to ChoiceSet if not already
        choice_set = ChoiceSet.create(choices) if not isinstance(choices, ChoiceSet) else choices
        
        # Get available choices based on game state
        valid_choices = choice_set.get_available_choices(scene_manager.game_state if scene_manager else self.game_state)
        
        if not valid_choices:
            self.console.print("[bold red]No available choices[/bold red]")
            return None
        
        # Create the panel with choices
        choice_texts = [f"[{i+1}] {choice.text}" for i, choice in enumerate(valid_choices)]
        choice_panel = Panel("\n".join(choice_texts), title="Choices", box=ROUNDED)
        
        while True:
            # Display the UI
            self.wrap_in_main_box(choice_panel, title, header_subtitle)
            
            # Get user input with a clean prompt that doesn't show all options
            self.console.print("Enter the number of your choice:")
            choice_input = self.get_input("Choice")
            
            # Check if it's a default action
            if choice_input in self.default_actions:
                continue
            
            # Try to convert to an integer
            try:
                choice_idx = int(choice_input) - 1
                if 0 <= choice_idx < len(valid_choices):
                    selected_choice = valid_choices[choice_idx]
                    
                    if scene_manager:
                        # Apply the choice's effect and handle scene transition
                        # using the scene manager
                        selected_choice.choose(scene_manager, f"Selected: {selected_choice.text}")
                    else:
                        # Legacy support for when no scene_manager is provided
                        if selected_choice._effect:
                            selected_choice._effect.apply(self.game_state)
                    
                    return selected_choice
                else:
                    self.console.print("Invalid choice number.")
            except ValueError:
                self.console.print("Please enter a number.")