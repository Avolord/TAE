"""
TALES Runner - Runs TALES scripts using the Text Adventure Engine.

This module provides a bridge between TALES scripts and the TAE engine,
converting parsed TALES elements into runnable TAE components.
"""
from typing import List, Dict, Any, Optional, Union
import argparse
from rich.console import Console

from tae_engine.game_state import GameState
from tae_engine.conditions import Condition
from tae_engine.effects import Effect
from tae_engine.choice import Choice, ChoiceSet
from tae_engine.scene_manager import SceneManager
from tae_engine.ui.rich_interface.dialogue_box import DialogueBox
from tae_engine.ui.rich_interface.choice_box import ChoiceBox
from tae_engine.ui.rich_interface.base_ui import BaseUI

from tae_engine.tales_parser import (
    TalesParser, 
    SceneElement, 
    DialogueElement, 
    ChoiceElement, 
    IfElement
)
from tae_engine.tales_lexer import TalesLexer


class TalesRunner:
    """
    Runs TALES scripts using the Text Adventure Engine.
    
    This class converts AST elements produced by the TalesParser into
    executable TAE components and manages the game flow.
    """
    
    def __init__(self, console: Optional[Console] = None):
        """
        Initialize the TalesRunner.
        
        Args:
            console: Optional Rich console instance for UI rendering
        """
        self.console = console or Console()
        self.scene_manager = SceneManager()
        self.ast = []
        
    def load_from_file(self, filename: str) -> None:
        """
        Load and parse a TALES script from a file.
        
        Args:
            filename: Path to the TALES script file
        """
        try:
            with open(filename, "r", encoding="utf-8") as file:
                tale_script = file.read()
            
            # Tokenize and parse the script
            self.console.print(f"[bold blue]Lexing[/bold blue] {filename}...")
            tokenized_lines = TalesLexer.tokenize(tale_script)
            
            self.console.print(f"[bold blue]Parsing[/bold blue] {filename}...")
            parser = TalesParser(tokenized_lines)
            self.ast = parser.parse()
            
            # Register scenes with the scene manager
            self._register_scenes()
            self.console.print(f"[bold green]Successfully loaded[/bold green] {len(self.ast)} scenes.")
        except Exception as e:
            self.console.print(f"[bold red]Error loading script:[/bold red] {e}")
            raise
    
    def _register_scenes(self) -> None:
        """Register all scenes from the AST with the scene manager."""
        for scene_element in self.ast:
            # Create a scene handler function that will process the scene's content
            scene_handler = self._create_scene_handler(scene_element)
            
            # Register the scene with the scene manager
            self.scene_manager.register_scene(scene_element.scene_name, scene_handler)
            self.console.print(f"  Registered scene: [cyan]{scene_element.scene_name}[/cyan]")
    
    def _create_scene_handler(self, scene_element: SceneElement):
        """
        Create a scene handler function for a scene element.
        
        Args:
            scene_element: The parsed scene element
            
        Returns:
            A function that handles the scene
        """
        # Store a reference to the scene element in the closure
        scene_content = scene_element.content
        scene_name = scene_element.scene_name
        
        # Define the scene handler function
        def scene_handler(scene_manager, **kwargs):
            # Initialize UI components
            dialogue_ui = DialogueBox(self.console)
            dialogue_ui.game_state = scene_manager.game_state
            dialogue_ui.scene_manager = scene_manager
            
            choice_ui = ChoiceBox(self.console)
            choice_ui.game_state = scene_manager.game_state
            choice_ui.scene_manager = scene_manager
            
            # Process each element in the scene
            self._process_scene_content(scene_content, scene_manager, dialogue_ui, choice_ui, scene_name)
        
        return scene_handler
    
    def _process_scene_content(
        self,
        content: List[Any],
        scene_manager: SceneManager,
        dialogue_ui: DialogueBox,
        choice_ui: ChoiceBox,
        scene_name: str = "unknown"
    ) -> None:
        """
        Process the content of a scene.
        
        Args:
            content: List of scene elements to process
            scene_manager: The SceneManager instance
            dialogue_ui: The DialogueBox UI component
            choice_ui: The ChoiceBox UI component
            scene_name: Name of the current scene for debugging
        """
        # Group consecutive choices to display together
        choice_group = []
        
        for element in content:
            # If we have accumulated choices and the next element is not a choice,
            # process the choice group before moving on
            if choice_group and not isinstance(element, ChoiceElement):
                self._process_choice_group(choice_group, scene_manager, choice_ui, scene_name)
                choice_group = []
            
            # Process the current element based on its type
            if isinstance(element, DialogueElement):
                self._process_dialogue(element, dialogue_ui, scene_manager)
            elif isinstance(element, ChoiceElement):
                # Add to the choice group to process later
                choice_group.append(element)
            elif isinstance(element, IfElement):
                # Evaluate the condition and process the appropriate branch
                self._process_if_element(element, scene_manager, dialogue_ui, choice_ui, scene_name)
        
        # Process any remaining choices
        if choice_group:
            self._process_choice_group(choice_group, scene_manager, choice_ui, scene_name)
    
    def _process_dialogue(
        self,
        dialogue: DialogueElement,
        dialogue_ui: DialogueBox,
        scene_manager: SceneManager
    ) -> None:
        """
        Process a dialogue element.
        
        Args:
            dialogue: The dialogue element to process
            dialogue_ui: The DialogueBox UI component
            scene_manager: The SceneManager instance
        """
        # Convert effects to Effect objects if any exist
        effects = None
        if dialogue.effects:
            effects = []
            for effect_str in dialogue.effects:
                try:
                    effect = Effect.create(effect_str)
                    effects.append(effect)
                except ValueError as e:
                    self.console.print(f"[bold yellow]Warning:[/bold yellow] Invalid effect '{effect_str}': {e}")
        
        # Show the dialogue
        dialogue_ui.show(
            dialogue.speaker,
            [dialogue.dialogue_text],  # Wrapped in a list as show() expects a list of lines
            effects=effects,
            scene_manager=scene_manager
        )
    
    def _process_choice_group(
        self,
        choices: List[ChoiceElement],
        scene_manager: SceneManager,
        choice_ui: ChoiceBox,
        scene_name: str = "unknown"
    ) -> None:
        """
        Process a group of choices.
        
        Args:
            choices: List of choice elements to process
            scene_manager: The SceneManager instance
            choice_ui: The ChoiceBox UI component
            scene_name: Name of the current scene for debugging
        """
        # TODO: Add full support for nested choices in the future
        # Currently, choices are flattened and all shown together
        
        # Convert ChoiceElements to TAE Choice objects
        tae_choices = []
        for choice_element in choices:
            try:
                # Create a Choice object
                tae_choice = self._create_tae_choice(choice_element)
                tae_choices.append(tae_choice)
            except ValueError as e:
                self.console.print(f"[bold yellow]Warning:[/bold yellow] Skipping invalid choice in scene '{scene_name}': {e}")
        
        if not tae_choices:
            self.console.print(f"[bold yellow]Warning:[/bold yellow] No valid choices in scene '{scene_name}'")
            return
        
        # Create a ChoiceSet
        choice_set = ChoiceSet(tae_choices)
        
        # Show the choices
        choice_ui.show(scene_name, choice_set, scene_manager, "What will you do?")
    
    def _create_tae_choice(self, choice_element: ChoiceElement) -> Choice:
        """
        Create a TAE Choice object from a ChoiceElement.
        
        Args:
            choice_element: The parsed choice element
            
        Returns:
            A TAE Choice object
        """
        # Parse condition string if it exists
        condition = None
        if choice_element.condition_str:
            try:
                condition = choice_element.condition_str.strip()
            except Exception as e:
                self.console.print(f"[bold yellow]Warning:[/bold yellow] Invalid condition '{choice_element.condition_str}': {e}")
        
        # Parse effect strings if they exist
        effect = None
        if choice_element.effects:
            if len(choice_element.effects) == 1:
                # Single effect
                effect = choice_element.effects[0].strip()
            else:
                # Multiple effects as a list
                effect = [e.strip() for e in choice_element.effects]
        
        # Create the Choice object
        return Choice(
            text=choice_element.text,
            condition=condition,
            effect=effect,
            next_scene=choice_element.transition
        )
    
    def _process_if_element(
        self,
        if_element: IfElement,
        scene_manager: SceneManager,
        dialogue_ui: DialogueBox,
        choice_ui: ChoiceBox,
        scene_name: str = "unknown"
    ) -> None:
        """
        Process an if element.
        
        Args:
            if_element: The if element to process
            scene_manager: The SceneManager instance
            dialogue_ui: The DialogueBox UI component
            choice_ui: The ChoiceBox UI component
            scene_name: Name of the current scene for debugging
        """
        # Convert the condition string to a Condition object
        condition_str = if_element.condition.representation.strip()
        
        try:
            # Create and evaluate the condition
            condition = Condition.create(condition_str)
            condition_met = condition.check(scene_manager.game_state)
            
            if condition_met:
                # Process the if branch
                self._process_scene_content(if_element.if_block, scene_manager, dialogue_ui, choice_ui, scene_name)
            elif if_element.else_block:
                # Process the else branch if it exists
                self._process_scene_content(if_element.else_block, scene_manager, dialogue_ui, choice_ui, scene_name)
                
        except ValueError as e:
            self.console.print(f"[bold yellow]Warning:[/bold yellow] Invalid condition '{condition_str}' in scene '{scene_name}': {e}")
            # Skip this condition block
    
    def run(self, starting_scene: Optional[str] = None) -> None:
        """
        Run the TALES script.
        
        Args:
            starting_scene: Optional name of the scene to start from
        """
        try:
            if not self.ast:
                self.console.print("[bold red]No script loaded. Call load_from_file() first.[/bold red]")
                return
            
            # Default to the first scene if none specified
            if not starting_scene and self.ast:
                starting_scene = self.ast[0].scene_name
                
            self.console.print(f"[bold green]Starting game[/bold green] from scene: [cyan]{starting_scene}[/cyan]")
            
            # Set up initial game state
            # You can customize this with default values
            self.scene_manager.game_state.update_stat("health", 100)
            
            # Run the game using the scene manager
            self.scene_manager.run_game(starting_scene)
            
            self.console.print("[bold green]Game completed.[/bold green]")
            
        except Exception as e:
            self.console.print(f"[bold red]Error running script:[/bold red] {e}")
            raise


def main():
    """Main entry point for running TALES scripts."""
    parser = argparse.ArgumentParser(description="Run a TALES script using the Text Adventure Engine")
    parser.add_argument("script", help="Path to the TALES script file")
    parser.add_argument("--scene", help="Name of the scene to start from")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    
    args = parser.parse_args()
    
    # Create the console with appropriate settings
    console = Console(highlight=True, log_path=False, log_time=args.debug)
    
    # Create the TalesRunner
    runner = TalesRunner(console)
    
    try:
        # Load and run the script
        runner.load_from_file(args.script)
        runner.run(args.scene)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        if args.debug:
            console.print("[bold red]Traceback:[/bold red]")
            import traceback
            traceback.print_exc()
        else:
            console.print("Run with --debug for more information.")


if __name__ == "__main__":
    main()