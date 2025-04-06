# ui/console_ui_placeholder.py
# (Place this in a separate 'ui' directory)

import os
import sys
from typing import List, Tuple, Optional, Dict, Any
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.box import ROUNDED

# Import the interface definition
# Adjust path if your structure differs
from tae_engine.ui_interface import UIInterface

class ConsoleUIPlaceholder(UIInterface):
    """A basic console implementation of the UIInterface using Rich."""

    def __init__(self):
        self.console = Console(highlight=True)

    def display_dialogue(self, speaker: str, line: str, is_end_of_sequence: bool) -> None:
        prompt_text = "Press Enter to continue..."
        nav_hint = f"\n\n[dim]{prompt_text}[/dim]"

        panel = Panel(
            f"{line}{nav_hint}",
            title=f"{speaker} says:",
            box=ROUNDED,
            border_style="blue",
            expand=False,
        )
        self.console.print(panel)
        # Simple blocking input
        input() # Waits for user to press Enter

    def prompt_choice(self, title: str, choices: List[Tuple[str, str, bool]]) -> Optional[str]:
        available_choices = [ (cid, text) for cid, text, is_available in choices if is_available ]

        if not available_choices:
            self.notify("There are no available choices right now.", "info")
            # In a real UI, might wait for 'next' or meta commands here
            # For placeholder, assume we just proceed if no choices shown
            return self.get_meta_input() # Allow meta commands even if no choices

        self.console.print(Panel(title, style="bold magenta", expand=False))

        choice_map = {}
        prompt_lines = []
        for i, (choice_id, choice_text) in enumerate(available_choices, 1):
            display_num = str(i)
            choice_map[display_num] = choice_id
            prompt_lines.append(f"  [cyan]{display_num}[/cyan]. {choice_text}")

        self.console.print("\n".join(prompt_lines))

        # Combine choice prompt with meta command prompt
        valid_inputs = list(choice_map.keys()) + ['s', 'l', 'u', 'q']
        prompt_text = f"Enter choice number (or s:save, l:load, u:undo, q:quit):"

        while True:
            raw_input = Prompt.ask(prompt_text).lower().strip()

            if raw_input in choice_map:
                return choice_map[raw_input] # Return the original choice_id
            elif raw_input == 's':
                return 'save' # Signal meta command
            elif raw_input == 'l':
                return 'load' # Signal meta command
            elif raw_input == 'u':
                return 'undo' # Signal meta command
            elif raw_input == 'q':
                return 'quit' # Signal meta command
            else:
                self.notify("Invalid input. Please try again.", "warning")


    def notify(self, message: str, level: str = "info") -> None:
        style = "dim"
        prefix = "[INFO]"
        if level == "warning":
            style = "yellow"
            prefix = "[WARN]"
        elif level == "error":
            style = "bold red"
            prefix = "[ERROR]"
        elif level == "success":
            style = "bold green"
            prefix = "[ OK ]"
        self.console.print(f"[{style}]{prefix} {message}[/]")

    def get_meta_input(self) -> Optional[str]:
         # Simplified version for when no choices are present
         prompt_text = "Enter command (s:save, l:load, u:undo, q:quit, Enter:next):"
         while True:
            raw_input = Prompt.ask(prompt_text, default="").lower().strip() # Default is 'next'
            if raw_input in ['s', 'l', 'u', 'q', '']:
                return raw_input if raw_input else 'next'
            else:
                self.notify("Invalid command.", "warning")


    def confirm_action(self, prompt_text: str) -> bool:
        return Confirm.ask(prompt_text, default=False)

    def get_save_filename(self) -> Optional[str]:
        filename = Prompt.ask("Enter filename to save (leave blank to cancel)").strip()
        if not filename:
            return None
        # Add .json extension if not present
        if not filename.lower().endswith(".json"):
            filename += ".json"
        return filename

    def get_load_filename(self, available_files: List[str]) -> Optional[str]:
        if not available_files:
            self.notify("No save files found.", "info")
            return None

        self.console.print("\nAvailable save files:")
        file_map = {}
        for i, filename in enumerate(available_files, 1):
            display_num = str(i)
            file_map[display_num] = filename
            self.console.print(f"  [cyan]{display_num}[/cyan]. {filename}")

        prompt_text = "Enter number of file to load (or 'c' to cancel):"
        while True:
            raw_input = Prompt.ask(prompt_text).lower().strip()
            if raw_input == 'c':
                return None
            if raw_input in file_map:
                return file_map[raw_input]
            else:
                self.notify("Invalid selection.", "warning")

