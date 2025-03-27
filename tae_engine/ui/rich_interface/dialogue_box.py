from typing import List
from rich.panel import Panel
from rich.box import ROUNDED

from tae_engine.ui.rich_interface import BaseUI

class DialogueBox(BaseUI):
    """UI component for displaying dialogue."""
    
    def show(self, speaker: str, dialogue_lines: List[str], header_subtitle: str = None) -> None:
        """
        Display dialogue lines with navigation options.
        
        Args:
            speaker: The name of the character speaking
            dialogue_lines: List of dialogue lines to display
            header_subtitle: Optional subtitle for the header
        """
        current_idx = 0
        
        while 0 <= current_idx < len(dialogue_lines):
            # Create the dialogue panel
            dialogue = dialogue_lines[current_idx]
            
            # Navigation indicators
            if current_idx == 0:
                navigation = "\[n]ext →"
            elif current_idx == len(dialogue_lines) - 1:
                navigation = "← \[p]rev"
            else:
                navigation = "← \[p]rev | \[n]ext →"
            
            dialogue_panel = Panel(
                f"{dialogue}\n\n{navigation} (press Enter for next)",
                title=f"{speaker} says:",
                box=ROUNDED
            )
            
            # Display the UI
            self.wrap_in_main_box(dialogue_panel, speaker, header_subtitle)
            
            # Get user input
            choice = self.get_input("", ["n", "p", ""])  # Empty string for just Enter
            
            # Check if it's a default action
            if choice in self.default_actions:
                continue
            
            # Handle navigation
            if (choice == 'n' or choice == '') and current_idx < len(dialogue_lines) - 1:
                current_idx += 1
            elif choice == 'p' and current_idx > 0:
                current_idx -= 1
            elif (choice == 'n' or choice == '') and current_idx == len(dialogue_lines) - 1:
                # At the end, pressing next/enter will exit
                return