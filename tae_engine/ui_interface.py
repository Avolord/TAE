# tae_engine/ui_interface.py
from typing import List, Tuple, Optional, Dict, Any, Protocol

class UIInterface(Protocol):
    """Defines the interface for UI interactions needed by the TalesRunner."""

    def display_dialogue(self, speaker: str, line: str, is_end_of_sequence: bool) -> None:
        """Displays a single line of dialogue and waits for acknowledgement.
        Args:
            speaker: The name of the character speaking.
            line: The dialogue text.
            is_end_of_sequence: True if this is the last line before choices or end.
        """
        ...

    def prompt_choice(self, title: str, choices: List[Tuple[str, str, bool]]) -> Optional[str]:
        """Prompts the user to make a choice from the available options.
        Args:
            title: A title or context for the choice prompt.
            choices: A list of tuples: (choice_id, choice_text, is_available).
                     The UI should only display available choices.
        Returns:
            The choice_id of the selected choice, or None if a meta-action
            (like quit, save, load, undo) was handled internally by the UI prompt.
        """
        ...

    def notify(self, message: str, level: str = "info") -> None:
        """Displays a notification message to the user (e.g., errors, save/load status).
        Levels could be 'info', 'warning', 'error', 'success'.
        """
        ...

    def get_meta_input(self) -> Optional[str]:
        """
        Gets input specifically for meta commands (save, load, undo, quit, next).
        This might be integrated into other prompts or called separately.
        Returns the command ('save', 'load', 'undo', 'quit', 'next') or None.
        """
        ...

    def confirm_action(self, prompt_text: str) -> bool:
        """Asks the user for a yes/no confirmation."""
        ...

    def get_save_filename(self) -> Optional[str]:
        """Asks the user for a filename to save the game."""
        ...

    def get_load_filename(self, available_files: List[str]) -> Optional[str]:
        """Presents available save files and asks the user to choose one."""
        ...

