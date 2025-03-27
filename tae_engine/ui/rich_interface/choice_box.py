from typing import List, Dict, Any
from rich.panel import Panel
from rich.box import ROUNDED

from tae_engine.ui.rich_interface import BaseUI

class ChoiceBox(BaseUI):
    """UI component for displaying choices."""
    
    def show(self, title: str, choices: List[Dict[str, Any]], header_subtitle: str = None) -> Dict[str, Any]:
        """
        Display a set of choices to the user.
        
        Args:
            title: The title of the choice box
            choices: List of choice dictionaries, each with 'text' and optionally 'condition' and 'consequence'
            header_subtitle: Optional subtitle for the header
            
        Returns:
            The selected choice dictionary
        """
        # Filter out choices that don't meet their conditions
        valid_choices = []
        for choice in choices:
            condition = choice.get('condition', lambda state: True)
            if callable(condition) and condition(self.game_state):
                valid_choices.append(choice)
        
        # Create the panel with choices
        choice_texts = [f"[{i+1}] {choice['text']}" for i, choice in enumerate(valid_choices)]
        choice_panel = Panel("\n".join(choice_texts), title="Choices", box=ROUNDED)
        
        while True:
            # Display the UI
            self.wrap_in_main_box(choice_panel, title, header_subtitle)
            
            # Get user input with a clean prompt that doesn't show all options
            self.console.print("Enter the number of your choice:")
            choice = self.get_input("Choice")
            
            # Check if it's a default action
            if choice in self.default_actions:
                continue
            
            # Try to convert to an integer
            try:
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(valid_choices):
                    selected_choice = valid_choices[choice_idx]
                    
                    # Execute consequence if it exists
                    consequence = selected_choice.get('consequence')
                    if callable(consequence):
                        consequence(self.game_state)
                    
                    return selected_choice
                else:
                    self.console.print("Invalid choice number.")
            except ValueError:
                self.console.print("Please enter a number.")