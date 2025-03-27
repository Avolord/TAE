from typing import Any, Dict, Tuple, Callable, Optional, Union, List
from rich.console import Console
from rich.panel import Panel
from rich.layout import Layout
from rich.box import ROUNDED
from rich.prompt import Prompt, Confirm
import os

from tae_engine.game_state import GameState

class BaseUI:
    """Base class for all UI elements."""
    
    def __init__(self, console: Console = None, game_state: GameState = None, scene_manager = None):
        """
        Initialize the UI with a console and game state.
        
        Args:
            console: The Rich console to use for display
            game_state: The game state to use (or create a new one if None)
            scene_manager: Optional scene manager to use for back operation
        """
        self.console = console or Console()
        self.game_state = game_state or GameState()
        self.scene_manager = scene_manager
        self.default_actions = {
            'q': ('Quit', self.quit_game),
            's': ('Save', self.save_game),
            'l': ('Load', self.load_game),
            'b': ('Back', self.back),
        }
    
    def clear_screen(self) -> None:
        """Clear the console screen."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def quit_game(self) -> None:
        """Exit the game."""
        if Confirm.ask("Are you sure you want to quit?"):
            exit(0)
    
    def save_game(self) -> None:
        """Save the current game state."""
        filename = Prompt.ask("Enter save filename (leave blank for auto-generated)", default="")
        saved_file = self.game_state.save(filename if filename else None)
        self.console.print(f"Game saved to {saved_file}")
    
    def load_game(self) -> None:
        """Load a game state from a file."""
        files = [f for f in os.listdir() if f.endswith('.sav')]
        
        if not files:
            self.console.print("No save files found.")
            return
        
        self.console.print("Available save files:")
        for i, file in enumerate(files, 1):
            self.console.print(f"{i}. {file}")
        
        choice = Prompt.ask("Enter the number of the save to load (or 'c' to cancel)")
        
        if choice.lower() == 'c':
            return
        
        try:
            index = int(choice) - 1
            if 0 <= index < len(files):
                self.game_state = GameState.load(files[index])
                self.console.print(f"Loaded game from {files[index]}")
                return self.game_state  # Return the loaded game state
            else:
                self.console.print("Invalid selection.")
        except ValueError:
            self.console.print("Invalid input.")
    
    def back(self) -> None:
        """Go back to previous state using scene manager if available."""
        if self.scene_manager:
            if self.scene_manager.back():
                self.console.print("Went back to previous state.")
                # Update the local game_state reference to match scene_manager
                self.game_state = self.scene_manager.game_state
            else:
                self.console.print("Can't go back any further.")
        else:
            # Legacy fallback for when no scene_manager is available
            self.console.print("Back function requires a scene manager.")
    
    def create_footer(self) -> Panel:
        """Create a footer with default actions."""
        actions = " | ".join([f"[bold]{key}[/bold]: {name}" for key, (name, _) in self.default_actions.items()])
        return Panel(actions, box=ROUNDED, style="dim")
    
    def create_header(self, title: str, subtitle: str = None) -> Panel:
        """Create a header with the given title and subtitle."""
        content = f"[bold]{title}[/bold]"
        if subtitle:
            content += f"\n{subtitle}"
        return Panel(content, box=ROUNDED, style="bold")
    
    def wrap_in_main_box(self, content: Any, header_title: str, header_subtitle: str = None) -> None:
        """Wrap the content in a main box with header and footer."""
        layout = Layout()
        layout.split(
            Layout(name="header"),
            Layout(name="main", ratio=8),
            Layout(name="footer")
        )
        
        layout["header"].update(self.create_header(header_title, header_subtitle))
        layout["main"].update(content)
        layout["footer"].update(self.create_footer())
        
        self.clear_screen()
        self.console.print(layout)
    
    def get_input(self, prompt_text: str, valid_choices: list = None) -> str:
        """
        Get user input with support for default actions.
        
        Args:
            prompt_text: Text to display in the prompt
            valid_choices: List of valid choices (apart from default actions)
            
        Returns:
            The user's choice
        """
        # Always include default actions in valid choices
        all_valid_choices = list(self.default_actions.keys())
        if valid_choices:
            all_valid_choices.extend(valid_choices)
        
        # Show only default actions in the prompt
        choice_prompt = f"{prompt_text} ({'/'.join(self.default_actions.keys())})"
        
        while True:
            choice = Prompt.ask(choice_prompt)
            
            # Check if it's a default action
            if choice in self.default_actions:
                _, action = self.default_actions[choice]
                action()
                return choice
            
            # If no valid_choices specified, accept any input
            if not valid_choices:
                return choice
            
            # Check if choice is valid
            if choice in valid_choices:
                return choice
            
            self.console.print(f"Invalid choice. Please enter one of: {', '.join(all_valid_choices)}")