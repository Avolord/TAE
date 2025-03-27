from typing import List, Optional, Union, Dict
from rich.panel import Panel
from rich.box import ROUNDED

from tae_engine.ui.rich_interface.base_ui import BaseUI
from tae_engine.effects import Effect


class DialogueBox(BaseUI):
    """UI component for displaying dialogue."""
    
    def show(
        self, 
        speaker: str, 
        dialogue_lines: List[str], 
        header_subtitle: Optional[str] = None,
        effects: Optional[List[Union[str, Dict, Effect]]] = None,
        scene_manager = None
    ) -> None:
        """
        Display dialogue lines with navigation options.
        
        Args:
            speaker: The name of the character speaking
            dialogue_lines: List of dialogue lines to display
            header_subtitle: Optional subtitle for the header
            effects: Optional list of effects to apply when dialogue is completed
            scene_manager: Optional scene manager to use for effects and back action
        """
        # Set scene_manager for back action
        self.scene_manager = scene_manager
        
        current_idx = 0
        
        while 0 <= current_idx < len(dialogue_lines):
            # Create the dialogue panel
            dialogue = dialogue_lines[current_idx]
            
            # Navigation indicators - only 'next' now since 'back' is a global action
            if current_idx < len(dialogue_lines) - 1:
                navigation = "\[n]ext → (or press Enter)"
            else:
                navigation = "(press Enter to continue)"
            
            dialogue_panel = Panel(
                f"{dialogue}\n\n{navigation}",
                title=f"{speaker} says:",
                box=ROUNDED
            )
            
            # Display the UI
            self.wrap_in_main_box(dialogue_panel, speaker, header_subtitle)
            
            # Get user input - removed 'p' option, kept 'n' and '' (Enter)
            choice = self.get_input("", ["n", ""])  # Empty string for just Enter
            
            # Check if it's a default action
            if choice in self.default_actions:
                continue
            
            # Handle navigation
            if (choice == 'n' or choice == '') and current_idx < len(dialogue_lines) - 1:
                current_idx += 1
            elif (choice == 'n' or choice == '') and current_idx == len(dialogue_lines) - 1:
                # At the end, pressing next/enter will exit
                # Apply any effects when dialogue is complete
                if effects and scene_manager:
                    for effect_data in effects:
                        scene_manager.apply_effect(effect_data, f"Effect from dialogue: {speaker}")
                return