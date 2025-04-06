# tae_engine/execution_manager.py

import copy
import traceback
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from rich.console import Console

# --- TAE Engine Core Imports ---
from tae_engine.game_state import GameState
from tae_engine.effects import Effect, CompoundEffect
from tae_engine.conditions import Condition
from tae_engine.choice import Choice, ChoiceSet

# --- Lexer and Parser Imports ---
# Assuming Element base class is defined here or imported appropriately
from tae_engine.tales_parser import (
    Element,
    SceneElement,
    DialogueElement,
    ChoiceElement,
    IfElement,
    Condition as ParserCondition, # Keep alias if needed
)

# --- UI Imports ---
# Import necessary UI components (adapt paths if needed)
from tae_engine.ui.rich_interface.base_ui import BaseUI
from tae_engine.ui.rich_interface.dialogue_box import DialogueBox
from tae_engine.ui.rich_interface.choice_box import ChoiceBox


# --- Helper Function to Add Parent Pointers ---
def add_parent_pointers(elements: List[Element], parent: Optional[Element]):
    """Recursively adds parent pointers to AST elements."""
    for element in elements:
        # Ensure parent attribute exists before setting
        if not hasattr(element, "parent"):
            element.parent = None # Initialize if missing
        element.parent = parent

        # Recurse into container elements
        if isinstance(element, SceneElement):
            add_parent_pointers(element.content, element)
        elif isinstance(element, IfElement):
            # Add parent to condition if it's treated as an element node
            if isinstance(element.condition, Element):
                if not hasattr(element.condition, "parent"):
                    element.condition.parent = None
                element.condition.parent = element
            add_parent_pointers(element.if_block, element)
            if element.else_block:
                add_parent_pointers(element.else_block, element)
        # Add elif for other container elements if needed (e.g., loops)


# --- Execution Manager Class ---
class ExecutionManager:
    """Manages game execution by traversing the TALES AST."""

    def __init__(
        self, ast: List[SceneElement], console: Console, game_state: GameState
    ):
        self.ast = ast
        self.console = console
        self.game_state = game_state
        self.current_element: Optional[Element] = None
        self.history: List[Tuple[Element, GameState]] = [] # For state management

        # Initialize UI Components
        # Pass self (manager) if UI needs to call back for actions like 'back'
        self.dialogue_ui = DialogueBox(self.console, self.game_state, self)
        self.choice_ui = ChoiceBox(self.console, self.game_state, self)
        # Add other UI components as needed

        # Add parent pointers to the loaded AST
        # Ensure Element base class has 'parent' attribute defined or handled
        if self.ast and not hasattr(self.ast[0], "parent"):
             # Add parent attribute dynamically if not present in class definition
             # This is less ideal than defining it in the Element class itself
             self.console.print("[dim]Dynamically adding 'parent' attribute to Elements.[/dim]")
             Element.parent = None
        add_parent_pointers(self.ast, None)


    def _find_scene_start_element(
        self, scene_name: str
    ) -> Optional[Element]:
        """Finds the first content element of a scene by name."""
        for scene in self.ast:
            if scene.scene_name == scene_name:
                # Return the scene itself, let set_start_point handle content
                # Or return first content element directly:
                return scene.content[0] if scene.content else None
        self.console.print(
            f"[bold red]Error: Scene '{scene_name}' not found.[/bold red]"
        )
        return None

    def _get_next_sequential_element(
        self, current_element: Element
    ) -> Optional[Element]:
        """Finds the next element in sequence within the parent container."""
        parent = getattr(current_element, "parent", None)
        if not parent:
            # If no parent, it might be a top-level scene element (shouldn't execute directly)
            # Or the root of the execution if starting mid-AST without full context.
            # For now, assume end of sequence if no parent.
            return None

        container: Optional[List[Element]] = None
        # Determine the list containing the current element
        if isinstance(parent, SceneElement):
            container = parent.content
        elif isinstance(parent, IfElement):
            # Check if element is in if_block or else_block
            try:
                idx = parent.if_block.index(current_element)
                container = parent.if_block
            except ValueError:
                try:
                    if parent.else_block:
                        idx = parent.else_block.index(current_element)
                        container = parent.else_block
                except (ValueError, AttributeError): # Handle if else_block is None or element not found
                     pass # Element might be the condition or structure is unexpected

        if container:
            try:
                current_index = container.index(current_element)
                if current_index + 1 < len(container):
                    # Return the next element in the same list
                    return container[current_index + 1]
                else:
                    # Reached end of this container, find what's after the parent container
                    return self._get_element_after_container(parent)
            except ValueError:
                 # Element not found in its expected container (shouldn't happen if parent pointers are correct)
                 self.console.print(f"[bold red]Internal Error: Element not found in its parent's container.[/bold red]")
                 return None

        # If element wasn't found in a known container type's list,
        # try finding what's next after the parent itself.
        return self._get_element_after_container(parent)


    def _get_element_after_container(
        self, container_element: Element
    ) -> Optional[Element]:
        """Finds the element that should execute after a container block finishes."""
        # After a block (like if/else) finishes, find what's next after the block element itself
        # by asking for the sequential element relative to the container element.
        return self._get_next_sequential_element(container_element)

    def set_start_point(self, start_ref: Optional[str] = None):
        """Sets the starting element for execution."""
        if start_ref is None:
            # Default to the first element of the first scene's content
            if self.ast and self.ast[0].content:
                self.current_element = self.ast[0].content[0]
            else:
                self.current_element = None
                self.console.print("[bold red]Error: Cannot start, AST is empty or first scene has no content.[/bold red]")
        else:
            # Assume start_ref is a scene name for now
            # TODO: Implement finding element by unique ID/path if needed
            self.current_element = self._find_scene_start_element(start_ref)

        if self.current_element:
             self.console.print(f"[dim]Execution starting point set to: {self.current_element}[/dim]")
        elif self.ast: # Only warn if AST exists but start point wasn't found/set
            self.console.print(
                f"[bold red]Warning: Could not set start point '{start_ref}'. Starting from beginning if possible, otherwise stopping.[/bold red]"
            )
            # Fallback to default start if specific one not found
            if self.ast and self.ast[0].content:
                self.current_element = self.ast[0].content[0]
                self.console.print(f"[dim]Fell back to starting at: {self.current_element}[/dim]")
            else:
                 self.current_element = None # Ensure it's None if fallback also fails


    def run(self):
        """Starts the execution loop from the current element."""
        if not self.current_element:
            self.console.print(
                "[bold red]Execution Error: No starting element set. Cannot run.[/bold red]"
            )
            return

        try:
            while self.current_element:
                # --- State Saving Hook (Future) ---
                # current_state_snapshot = copy.deepcopy(self.game_state)
                # current_element_ref = self.get_element_reference(self.current_element) # Needs stable ref/ID
                # self.history.append((current_element_ref, current_state_snapshot))
                # ---

                next_element = self._execute_element(self.current_element)
                self.current_element = next_element

            self.console.print("\n[bold green]Story concluded.[/bold green]")

        except Exception as e:
             self.console.print(f"\n[bold red]Runtime Error:[/bold red] {e}")
             # Check if current_element exists before trying to print it
             current_executing = self.current_element if hasattr(self, 'current_element') else "Unknown"
             self.console.print(f"Error occurred near element: {current_executing}")
             self.console.print("\n[bold red]Traceback:[/bold red]")
             traceback.print_exc()


    def _execute_element(self, element: Element) -> Optional[Element]:
        """Executes a single AST element and returns the next element."""
        self.console.print(f"[dim]Executing: {element}[/dim]") # Debug output

        if isinstance(element, DialogueElement):
            return self._execute_dialogue(element)
        elif isinstance(element, ChoiceElement):
            # Choice execution needs to handle grouping
            return self._handle_choice_start(element)
        elif isinstance(element, IfElement):
            return self._execute_if(element)
        # Add elif for other element types (e.g., SetVariableElement, etc.)
        else:
            self.console.print(
                f"[bold yellow]Warning:[/bold yellow] Skipping unknown element type: {type(element)}"
            )
            return self._get_next_sequential_element(element)

    def _apply_effects(self, effect_sources: Union[List[str], List[Effect]], context: str):
        """Helper to parse and apply effects."""
        effects_to_apply = []
        if not effect_sources:
            return

        for source in effect_sources:
            try:
                if isinstance(source, str):
                    effect = Effect.create(source.strip())
                elif isinstance(source, Effect):
                    effect = source # Already created
                else:
                    # Handle list of strings/effects if passed directly
                    if isinstance(source, list):
                         # Recursively handle lists (e.g., from ChoiceElement.effects)
                         self._apply_effects(source, context)
                         continue # Skip appending the list itself
                    else:
                        raise ValueError(f"Invalid effect source type: {type(source)}")
                effects_to_apply.append(effect)
            except ValueError as e:
                self.console.print(
                    f"[bold yellow]Warning:[/bold yellow] Invalid effect '{source}' in {context}: {e}"
                )

        # Apply effects if any were successfully parsed
        if effects_to_apply:
            # Use CompoundEffect if multiple, direct apply if single
            if len(effects_to_apply) > 1:
                compound_effect = CompoundEffect(effects_to_apply)
                # --- State Saving Hook (Future) ---
                # self.save_state_before_action(f"Applying compound effect from {context}")
                # ---
                compound_effect.apply(self.game_state)
                self.console.print(f"[dim]Applied compound effect ({context})[/dim]")
            elif len(effects_to_apply) == 1:
                 # --- State Saving Hook (Future) ---
                 # self.save_state_before_action(f"Applying effect from {context}")
                 # ---
                 effects_to_apply[0].apply(self.game_state)
                 self.console.print(f"[dim]Applied effect ({context}): {effects_to_apply[0]}[/dim]")


    def _execute_dialogue(self, element: DialogueElement) -> Optional[Element]:
        """Handles displaying dialogue and applying its effects."""
        self.dialogue_ui.game_state = self.game_state # Ensure UI has latest state
        self.dialogue_ui.scene_manager = self # Pass manager reference

        # DialogueBox.show displays and waits for user to press Enter/Next
        self.dialogue_ui.show(
            speaker=element.speaker,
            dialogue_lines=[element.dialogue_text], # show expects a list
            # Effects are applied *after* showing and proceeding
        )

        # Apply effects after dialogue is acknowledged
        self._apply_effects(element.effects, f"dialogue by {element.speaker}")

        # Proceed to the next element in sequence
        return self._get_next_sequential_element(element)

    def _handle_choice_start(self, first_choice_element: ChoiceElement) -> Optional[Element]:
        """Handles a group of consecutive choices."""
        choice_group = [first_choice_element]
        parent = getattr(first_choice_element, "parent", None)
        container = None
        last_choice_in_group = first_choice_element # Track the last element of the group

        # Find the container (if_block, else_block, scene content)
        if parent:
            if isinstance(parent, SceneElement): container = parent.content
            elif isinstance(parent, IfElement):
                try: parent.if_block.index(first_choice_element); container = parent.if_block
                except ValueError:
                    try:
                        if parent.else_block: parent.else_block.index(first_choice_element); container = parent.else_block
                    except (ValueError, AttributeError): pass

        # Find subsequent choices in the same container
        if container:
            try:
                start_index = container.index(first_choice_element)
                next_index = start_index + 1
                while next_index < len(container) and isinstance(container[next_index], ChoiceElement):
                    choice_group.append(container[next_index])
                    last_choice_in_group = container[next_index] # Update last element
                    next_index += 1
            except ValueError: pass # Should not happen

        # Convert AST ChoiceElements to TAE Choice objects
        tae_choices = []
        for choice_elem in choice_group:
            try:
                condition_obj = None
                if choice_elem.condition_str:
                    try:
                        condition_obj = Condition.create(choice_elem.condition_str.strip())
                    except Exception as e:
                        self.console.print(f"[bold yellow]Warning:[/bold yellow] Invalid condition '{choice_elem.condition_str}': {e}. Choice may be unavailable.")

                # Parse effects (string to Effect objects)
                effect_obj = None
                if choice_elem.effects:
                     parsed_effects = []
                     for eff_str in choice_elem.effects:
                         try:
                             # Ensure effect strings are stripped
                             parsed_effects.append(Effect.create(eff_str.strip()))
                         except ValueError as e:
                             self.console.print(f"[bold yellow]Warning:[/bold yellow] Invalid effect '{eff_str}' in choice: {e}")
                     if len(parsed_effects) == 1:
                         effect_obj = parsed_effects[0]
                     elif len(parsed_effects) > 1:
                         effect_obj = CompoundEffect(parsed_effects)

                tae_choice = Choice(
                    text=choice_elem.text,
                    condition=condition_obj, # Pass parsed Condition
                    effect=effect_obj,       # Pass parsed Effect(s)
                    next_scene=choice_elem.transition # Keep transition target name
                )
                tae_choices.append(tae_choice)
            except Exception as e: # Catch potential errors during Choice creation
                self.console.print(f"[bold yellow]Warning:[/bold yellow] Skipping invalid choice element {choice_elem}: {e}")

        if not tae_choices:
            self.console.print(f"[bold yellow]Warning:[/bold yellow] No valid choices processed starting at {first_choice_element}.")
            # Proceed sequentially after the last element scanned in the group
            return self._get_next_sequential_element(last_choice_in_group)

        choice_set = ChoiceSet(tae_choices)

        # Use ChoiceBox UI - **Requires modification/verification**
        self.choice_ui.game_state = self.game_state
        self.choice_ui.scene_manager = self

        # Assumes ChoiceBox.show filters choices and returns the selected TAE Choice object.
        chosen_tae_choice: Optional[Choice] = self.choice_ui.show(
             title="Your Choice", # TODO: Get title context if possible
             choices=choice_set,
        )

        if chosen_tae_choice:
            # Apply effect associated with the *chosen* TAE Choice
            # Pass the already created Effect object(s) from the Choice
            self._apply_effects([chosen_tae_choice._effect] if chosen_tae_choice._effect else [], f"choice '{chosen_tae_choice.text}'")

            # Determine next element
            if chosen_tae_choice.next_scene:
                # Transition to the start of the specified scene
                return self._find_scene_start_element(chosen_tae_choice.next_scene)
            else:
                # No transition, continue sequentially after the *entire* choice block
                return self._get_next_sequential_element(last_choice_in_group)
        else:
            # No choice selected (e.g., default action handled by UI, or no available choices shown)
            # Assume UI handled quit/load/back appropriately. If just no choice made, proceed.
             self.console.print("[dim]No choice made or default action handled by UI.[/dim]")
             # Proceed sequentially after the last element scanned in the group
             return self._get_next_sequential_element(last_choice_in_group)


    def _execute_if(self, element: IfElement) -> Optional[Element]:
        """Handles conditional execution (if/else)."""
        try:
            # Condition representation is stored in the ParserCondition object
            condition_str = element.condition.representation.strip()
            condition = Condition.create(condition_str)
            condition_met = condition.check(self.game_state)
            self.console.print(f"[dim]Condition '{condition_str}' met: {condition_met}[/dim]")
        except ValueError as e:
            self.console.print(f"[bold yellow]Warning:[/bold yellow] Invalid condition '{element.condition.representation}' in if-statement: {e}")
            # Skip the entire if structure if condition is invalid
            return self._get_next_sequential_element(element)

        if condition_met:
            if element.if_block:
                # Start execution at the first element of the if-block
                return element.if_block[0]
            else:
                # Empty if-block, find what's after the IfElement itself
                return self._get_next_sequential_element(element)
        else: # Condition not met
            if element.else_block:
                 # Start execution at the first element of the else-block
                return element.else_block[0]
            else:
                # No else-block, find what's after the IfElement itself
                return self._get_next_sequential_element(element)

    # --- Back/Save/Load Stubs (Future Implementation) ---
    def back(self):
        """Reverts to the previous state in history."""
        # Needs history implementation with state snapshots and element refs
        self.console.print("[bold yellow]Feature 'back' not yet implemented.[/bold yellow]")
        # Should potentially return True/False if successful
        # And update self.current_element and self.game_state

    def save_game(self, filename: Optional[str] = None) -> Optional[str]:
        """Saves the current game state and execution point."""
        # Needs serialization of game_state and current_element reference
        self.console.print("[bold yellow]Feature 'save' not yet implemented.[/bold yellow]")
        return None # Placeholder

    def load_game(self, filename: str) -> bool:
         """Loads game state and restores execution point."""
         # Needs deserialization and setting self.game_state and self.current_element
         self.console.print("[bold yellow]Feature 'load' not yet implemented.[/bold yellow]")
         return False # Placeholder

