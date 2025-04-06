# tae_engine/runner.py
import json
import os
import copy
import logging
import traceback
from typing import List, Tuple, Optional, Dict, Any, Union

# Engine components
from tae_engine.game_state import GameState
from tae_engine.effects import Effect, CompoundEffect
from tae_engine.conditions import Condition
from tae_engine.choice import Choice # Assuming Choice is adapted if needed
from tae_engine.tales_parser import (
    Element, SceneElement, DialogueElement, ChoiceElement, IfElement
)
# UI Interface
from tae_engine.ui_interface import UIInterface

# --- Logger Setup ---
# Configure logging to write to a file
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log_handler = logging.FileHandler('tae_runner.log', mode='w') # Overwrite log each run
log_handler.setFormatter(log_formatter)

logger = logging.getLogger('TalesRunner')
logger.setLevel(logging.DEBUG) # Log everything from DEBUG level up
logger.addHandler(log_handler)
logger.propagate = False # Prevent duplicate logging if root logger is configured


class TalesRunner:
    """Drives the execution of a TALES script using its AST,
       handling state, history, save/load, and UI interaction."""

    def __init__(self, ast: List[SceneElement], ui: UIInterface):
        logger.info("Initializing TalesRunner...")
        self.ast = ast # AST has stable IDs and parent refs from parser
        self.ui = ui
        self.game_state: GameState = GameState() # Start fresh
        # History stores (GameState dict, executed element's stable string ID)
        # The ID is the one *executed* to reach the state in the tuple
        self.history: List[Tuple[Dict, Optional[str]]] = []
        self.current_element_id: Optional[str] = None # Stable string ID
        self.element_map: Dict[str, Element] = {} # Map stable string ID to Element

        try:
            self._build_element_map(self.ast)
            self._set_initial_element()
            # Save the very initial state before anything happens
            self._save_history_snapshot(None) # Pass None for element_id for initial state
            logger.info("TalesRunner initialized successfully.")
        except Exception as e:
            logger.critical(f"Failed to initialize TalesRunner: {e}", exc_info=True)
            # Optionally raise the exception or notify UI and exit
            self.ui.notify(f"Fatal Error during initialization: {e}", "error")
            raise # Re-raise critical errors

    def _build_element_map(self, elements: List[Element]):
        """Recursively populates the element_map using pre-assigned stable IDs."""
        logger.debug("Building element map...")
        count = 0
        queue = list(elements)
        while queue:
            element = queue.pop(0)
            if hasattr(element, 'element_id') and element.element_id is not None:
                if element.element_id in self.element_map:
                     logger.warning(f"Duplicate element ID found: {element.element_id}. Overwriting map entry. Check parser ID logic.")
                self.element_map[element.element_id] = element
                count += 1
                # Add children to queue
                if isinstance(element, SceneElement):
                    queue.extend(element.content)
                elif isinstance(element, IfElement):
                    queue.extend(element.if_block)
                    if element.else_block:
                        queue.extend(element.else_block)
                # Add elif for other container types
            else:
                 logger.warning(f"Element {type(element)} found without a stable ID during map build.")
        logger.debug(f"Element map built with {count} entries.")


    def _set_initial_element(self):
        """Sets the starting element ID using stable IDs."""
        if self.ast:
            first_scene = self.ast[0]
            if hasattr(first_scene, 'content') and first_scene.content:
                 # Get the stable ID of the first content element
                 self.current_element_id = first_scene.content[0].element_id
                 logger.info(f"Initial element set to ID: {self.current_element_id}")
            else:
                 self.current_element_id = None
                 logger.warning(f"First scene '{getattr(first_scene, 'scene_name', 'Unknown')}' has no content. Cannot set initial element.")
                 self.ui.notify(f"Warning: First scene '{getattr(first_scene, 'scene_name', 'Unknown')}' is empty.", "warning")
        else:
            self.current_element_id = None
            logger.error("AST is empty, cannot set initial element.")
            self.ui.notify("Error: The story script appears to be empty.", "error")

    def _get_element_by_id(self, element_id: Optional[str]) -> Optional[Element]:
        """Retrieves an element object from the map using its ID."""
        if element_id is None:
            return None
        element = self.element_map.get(element_id)
        if element is None:
             logger.warning(f"Attempted to get element with non-existent ID: {element_id}")
        return element

    # --- Navigation Helpers (Using Parent References) ---
    def _get_next_sequential_element_id(self, current_element_id: str) -> Optional[str]:
        """Finds the ID of the next element in sequence using parent references."""
        current_element = self._get_element_by_id(current_element_id)
        if not current_element:
            logger.error(f"Cannot find next sequential: current element ID '{current_element_id}' not found in map.")
            return None

        parent = getattr(current_element, "parent", None)
        if not parent:
            logger.debug(f"Element {current_element_id} has no parent, sequence ends.")
            return None # Top-level element or end of a branch

        container: Optional[List[Element]] = None
        # Determine the list containing the current element
        if isinstance(parent, SceneElement): container = parent.content
        elif isinstance(parent, IfElement):
            # Check object identity for block belonging
            if parent.if_block is not None and current_element in parent.if_block:
                 container = parent.if_block
            elif parent.else_block is not None and current_element in parent.else_block:
                 container = parent.else_block
            else:
                 logger.warning(f"Element {current_element_id} not found in parent IfElement's blocks.")

        if container:
            try:
                current_index = container.index(current_element)
                if current_index + 1 < len(container):
                    next_element = container[current_index + 1]
                    logger.debug(f"Next sequential element is index {current_index + 1} in container: {getattr(next_element, 'element_id', 'N/A')}")
                    return getattr(next_element, 'element_id', None)
                else:
                    # Reached end of this container, find what's after the parent container
                    logger.debug(f"Reached end of container for element {current_element_id}. Looking after parent {getattr(parent, 'element_id', 'N/A')}.")
                    return self._get_element_id_after_container(parent)
            except ValueError:
                 logger.error(f"Element {current_element_id} not found in its identified container (parent {getattr(parent, 'element_id', 'N/A')}).")
                 return None # Element not found where expected

        logger.debug(f"Could not determine container for element {current_element_id}. Looking after parent {getattr(parent, 'element_id', 'N/A')}.")
        return self._get_element_id_after_container(parent)


    def _get_element_id_after_container(self, container_element: Element) -> Optional[str]:
         """Finds the ID of the element after a container block finishes."""
         container_id = getattr(container_element, 'element_id', None)
         if container_id is None:
             logger.warning(f"Container element {type(container_element)} lacks an ID, cannot find element after it.")
             return None
         logger.debug(f"Finding element after container {container_id}")
         # Use the same logic as _get_next_sequential_element_id, but start from the container
         return self._get_next_sequential_element_id(container_id)

    # --- State and History Management ---
    def _save_history_snapshot(self, executed_element_id: Optional[str]):
        """Saves the current game state and the ID of the element just run."""
        try:
            # Use deepcopy ONLY if GameState contains mutable objects not handled by to_dict
            # If to_dict creates a full representation, deepcopy might be redundant
            state_snapshot = self.game_state.to_dict() # Get serializable state
            self.history.append((state_snapshot, executed_element_id))
            logger.debug(f"History snapshot saved. Element executed: {executed_element_id}. History depth: {len(self.history)}")
        except Exception as e:
            logger.error(f"Failed to save history snapshot: {e}", exc_info=True)


    # --- Main Execution Loop ---
    def run(self):
        """Main execution loop."""
        logger.info("Starting execution loop.")
        if not self.current_element_id:
            logger.error("Execution halted: No starting element ID set.")
            self.ui.notify("Cannot start the story (no starting point found).", "error")
            return

        execution_active = True
        while execution_active and self.current_element_id:
            element_to_execute = self._get_element_by_id(self.current_element_id)

            if not element_to_execute:
                logger.error(f"Execution halted: Element with ID '{self.current_element_id}' not found in map.")
                self.ui.notify(f"Story Error: Cannot find expected story element (ID: {self.current_element_id}).", "error")
                break # Stop execution

            executed_id = self.current_element_id
            logger.info(f"Executing element ID: {executed_id} ({type(element_to_execute).__name__})")
            next_element_id_or_command: Optional[Union[str]] = None # Expect string ID or command

            # --- Execute Element ---
            try:
                if isinstance(element_to_execute, DialogueElement):
                    next_element_id_or_command = self._execute_dialogue(element_to_execute)
                elif isinstance(element_to_execute, ChoiceElement):
                    next_element_id_or_command = self._handle_choice_start(element_to_execute)
                elif isinstance(element_to_execute, IfElement):
                    next_element_id_or_command = self._execute_if(element_to_execute)
                # Add elif for other element types
                else:
                    logger.warning(f"Skipping unknown element type: {type(element_to_execute)} with ID {executed_id}")
                    next_element_id_or_command = self._get_next_sequential_element_id(executed_id)

                # --- Handle Meta Commands or None ---
                if next_element_id_or_command is None:
                    logger.info("Execution sequence ended (next element is None).")
                    execution_active = False # End of story or branch
                    self.current_element_id = None
                elif isinstance(next_element_id_or_command, str):
                    command_or_id = next_element_id_or_command
                    if command_or_id == 'save':
                        self.save_game()
                        # Continue from the *same* element after saving
                        self.current_element_id = executed_id
                    elif command_or_id == 'load':
                        if self.load_game():
                             # load_game sets current_element_id, loop continues naturally
                             logger.info(f"Load successful. Resuming at element ID: {self.current_element_id}")
                        else:
                             # Load failed or cancelled, continue from same element
                             logger.info("Load cancelled or failed. Resuming execution.")
                             self.current_element_id = executed_id
                    elif command_or_id == 'undo':
                        self.undo()
                        # undo sets current_element_id, loop continues naturally
                        # If undo fails and sets ID to None, loop will terminate
                        logger.info(f"Undo attempted. Resuming at element ID: {self.current_element_id}")
                    elif command_or_id == 'quit':
                        if self.ui.confirm_action("Are you sure you want to quit?"):
                            logger.info("User chose to quit.")
                            execution_active = False
                            self.current_element_id = None # Ensure loop terminates
                        else:
                            logger.info("User cancelled quit.")
                            self.current_element_id = executed_id # Continue from same element
                    elif command_or_id == 'next': # Handle explicit 'next' from UI (e.g., after no choices)
                         logger.debug("Received 'next' command from UI.")
                         self.current_element_id = self._get_next_sequential_element_id(executed_id)
                    else: # It's a normal element ID string
                         self.current_element_id = command_or_id
                else: # Should not happen if methods return str or None
                     logger.error(f"Unexpected return type from execution method: {type(next_element_id_or_command)}. Halting.")
                     execution_active = False
                     self.current_element_id = None


            except Exception as e:
                logger.error(f"Runtime Error during execution of element {executed_id}: {e}", exc_info=True)
                self.ui.notify(f"An unexpected error occurred in the story: {e}", "error")
                traceback.print_exc() # Also print to console for immediate visibility if possible
                execution_active = False # Halt execution on unhandled error
                self.current_element_id = None

        # --- End of Loop ---
        if not execution_active and self.current_element_id is None:
             logger.info("Execution loop terminated normally.")
             # Only show "concluded" if it wasn't due to an error handled above
             if not isinstance(next_element_id_or_command, Exception): # Check if last step was error? Needs better flag.
                 self.ui.notify("Story concluded.", "success")
        elif not execution_active:
             logger.info("Execution loop terminated by quit or error.")
        else: # Should not happen if loop terminates correctly
             logger.warning("Execution loop exited unexpectedly.")


    # --- Effect Application ---
    def _apply_effects(self, effect_sources: Union[List[str], List[Effect]], context_element_id: Optional[str]):
        """Parses, saves history snapshot, and applies effects."""
        effects_to_apply = []
        if not effect_sources: return

        logger.debug(f"Parsing effects for element {context_element_id}: {effect_sources}")
        for source in effect_sources:
            try:
                # Handle potential nested lists if Effect.create doesn't
                if isinstance(source, list):
                    logger.warning(f"Found nested list in effect sources for {context_element_id}. Flattening.")
                    self._apply_effects(source, context_element_id) # Recurse
                    continue

                effect = Effect.create(source.strip()) if isinstance(source, str) else source
                if isinstance(effect, Effect):
                    effects_to_apply.append(effect)
                else:
                     logger.warning(f"Invalid effect source type encountered: {type(source)} for element {context_element_id}")
            except ValueError as e:
                logger.warning(f"Invalid effect string '{source}' for element {context_element_id}: {e}")
            except Exception as e:
                 logger.error(f"Unexpected error parsing effect '{source}' for {context_element_id}: {e}", exc_info=True)


        if not effects_to_apply:
            logger.debug(f"No valid effects to apply for element {context_element_id}.")
            return

        # Save state *before* applying effects
        logger.debug(f"Saving history snapshot before applying effects for {context_element_id}")
        self._save_history_snapshot(context_element_id)

        # Apply the effects
        logger.info(f"Applying {len(effects_to_apply)} effect(s) for element {context_element_id}")
        try:
            # Combine into CompoundEffect if multiple for single application logic
            if len(effects_to_apply) > 1:
                CompoundEffect(effects_to_apply).apply(self.game_state)
                logger.debug(f"Applied compound effect for {context_element_id}.")
            elif len(effects_to_apply) == 1:
                effects_to_apply[0].apply(self.game_state)
                logger.debug(f"Applied single effect for {context_element_id}: {effects_to_apply[0]}")
        except Exception as e:
             logger.error(f"Error applying effects for element {context_element_id}: {e}", exc_info=True)
             self.ui.notify(f"Error applying effect: {e}", "error")
             # Consider if execution should halt here

    # --- Element Execution Logic ---
    def _execute_dialogue(self, element: DialogueElement) -> Optional[str]:
        """Handles dialogue display and effects. Returns next element ID or command."""
        logger.debug(f"Executing dialogue: Speaker={element.speaker}, Text='{element.dialogue_text[:30]}...'")
        next_id = self._get_next_sequential_element_id(element.element_id)
        next_element = self._get_element_by_id(next_id)
        is_end = not isinstance(next_element, DialogueElement)
        logger.debug(f"Is end of dialogue sequence: {is_end}")

        # Display dialogue via UI - UI handles waiting for 'Enter'/'next'
        self.ui.display_dialogue(element.speaker, element.dialogue_text, is_end)
        # TODO: The UI needs a way to signal meta-commands (s,l,u,q) during this wait.
        # For now, assume display_dialogue blocks until Enter, then we apply effects.
        # A better UI would integrate the meta-command check.

        # Apply effects *after* dialogue is shown and acknowledged
        self._apply_effects(element.effects, element.element_id)

        # Return the ID of the next element
        return self._get_next_sequential_element_id(element.element_id)


    def _handle_choice_start(self, first_choice_element: ChoiceElement) -> Optional[str]:
        """Handles a group of choices. Returns next element ID or command."""
        logger.debug(f"Handling choice block starting with element {first_choice_element.element_id}")
        choice_group_elements = [first_choice_element]
        last_choice_in_group_id = first_choice_element.element_id

        # --- Logic to find consecutive ChoiceElements (using parent refs) ---
        parent = getattr(first_choice_element, "parent", None)
        if parent:
            container: Optional[List[Element]] = None
            # Determine container... (same logic as _get_next_sequential_element_id)
            if isinstance(parent, SceneElement): container = parent.content
            elif isinstance(parent, IfElement):
                 if parent.if_block is not None and first_choice_element in parent.if_block: container = parent.if_block
                 elif parent.else_block is not None and first_choice_element in parent.else_block: container = parent.else_block

            if container:
                try:
                    start_index = container.index(first_choice_element)
                    next_index = start_index + 1
                    while next_index < len(container) and isinstance(container[next_index], ChoiceElement):
                        choice_elem = container[next_index]
                        choice_group_elements.append(choice_elem)
                        last_choice_in_group_id = choice_elem.element_id # Update last ID
                        next_index += 1
                    logger.debug(f"Choice group found with {len(choice_group_elements)} elements, ending with ID {last_choice_in_group_id}.")
                except ValueError: pass # Should not happen
        # --- End consecutive choice finding ---

        # Prepare choices for the UI: (id, text, is_available)
        ui_choices: List[Tuple[str, str, bool]] = []
        available_choice_objects: Dict[str, Choice] = {} # Map stable ID to TAE Choice obj

        logger.debug("Evaluating conditions for choices...")
        for choice_elem in choice_group_elements:
            condition_met = True
            condition_str_for_log = "None"
            if choice_elem.condition_str:
                condition_str_for_log = choice_elem.condition_str
                try:
                    condition = Condition.create(choice_elem.condition_str.strip())
                    condition_met = condition.check(self.game_state)
                except ValueError as e:
                    logger.warning(f"Invalid condition '{choice_elem.condition_str}' for choice ID {choice_elem.element_id}: {e}")
                    condition_met = False # Treat as unavailable

            logger.debug(f"Choice ID {choice_elem.element_id}: Text='{choice_elem.text[:30]}...', Condition='{condition_str_for_log}', Available={condition_met}")
            ui_choices.append((choice_elem.element_id, choice_elem.text, condition_met))

            # If available, create the TAE Choice object for later use
            if condition_met:
                try:
                    # Parse effects now
                    effect_obj = None
                    if choice_elem.effects:
                        parsed_fx = []
                        for eff_str in choice_elem.effects:
                             if eff_str and eff_str.strip(): # Ensure not empty
                                 try:
                                     parsed_fx.append(Effect.create(eff_str.strip()))
                                 except ValueError as e:
                                     logger.warning(f"Invalid effect string '{eff_str}' in choice ID {choice_elem.element_id}: {e}")
                        if len(parsed_fx) == 1: effect_obj = parsed_fx[0]
                        elif len(parsed_fx) > 1: effect_obj = CompoundEffect(parsed_fx)

                    available_choice_objects[choice_elem.element_id] = Choice(
                        text=choice_elem.text,
                        effect=effect_obj, # Use pre-parsed effect
                        next_scene=choice_elem.transition,
                    )
                except Exception as e:
                     logger.error(f"Error creating TAE Choice object for ID {choice_elem.element_id}: {e}", exc_info=True)
                     # Remove from ui_choices if creation failed? Or rely on available_choice_objects check later.
                     # Let's ensure it's marked unavailable in ui_choices if we hit an error here.
                     # Find and update the tuple in ui_choices (less efficient but safer)
                     for i, (eid, txt, _) in enumerate(ui_choices):
                         if eid == choice_elem.element_id:
                             ui_choices[i] = (eid, txt, False)
                             break


        # Prompt user via UI
        # UI returns the element_id (str) of the chosen choice, or a meta-command string, or None
        logger.debug("Prompting user for choice via UI.")
        chosen_id_or_command = self.ui.prompt_choice("Your choice:", ui_choices)
        logger.info(f"UI returned from choice prompt: {chosen_id_or_command}")

        if chosen_id_or_command in ['save', 'load', 'undo', 'quit', 'next', None]:
            # UI handled meta action or returned None (e.g., no available choices shown)
            # Return the command string/None so the main loop can handle it
            # If None, main loop should probably proceed sequentially.
            return chosen_id_or_command if chosen_id_or_command else self._get_next_sequential_element_id(last_choice_in_group_id)

        elif chosen_id_or_command in available_choice_objects:
            # User selected a valid, available choice ID (string)
            chosen_element_id = chosen_id_or_command
            chosen_tae_choice = available_choice_objects[chosen_element_id]
            logger.info(f"User selected choice ID: {chosen_element_id}")

            # Apply effects associated with the choice (saves history snapshot)
            self._apply_effects([chosen_tae_choice._effect] if chosen_tae_choice._effect else [], chosen_element_id)

            # Determine next element ID
            if chosen_tae_choice.next_scene:
                logger.info(f"Choice triggers transition to scene: {chosen_tae_choice.next_scene}")
                # Find the starting element ID of the target scene
                target_scene_start_id = None
                for scene in self.ast:
                    if scene.scene_name == chosen_tae_choice.next_scene:
                        if scene.content:
                            target_scene_start_id = scene.content[0].element_id
                            logger.debug(f"Found target scene start element ID: {target_scene_start_id}")
                        else:
                             logger.warning(f"Transition target scene '{chosen_tae_choice.next_scene}' is empty.")
                        break
                if target_scene_start_id:
                    return target_scene_start_id
                else:
                    logger.error(f"Transition target scene '{chosen_tae_choice.next_scene}' not found.")
                    self.ui.notify(f"Error: Cannot find scene '{chosen_tae_choice.next_scene}'.", "error")
                    # Fallback: proceed sequentially after choice block
                    return self._get_next_sequential_element_id(last_choice_in_group_id)
            else:
                # No transition, continue sequentially after the *entire* choice block
                logger.debug("No transition specified, continuing sequentially.")
                return self._get_next_sequential_element_id(last_choice_in_group_id)
        else:
             # Should not happen if UI returns valid IDs or commands
             logger.error(f"Internal Error: Invalid choice ID '{chosen_id_or_command}' received from UI.")
             self.ui.notify(f"Internal Error processing choice.", "error")
             return self._get_next_sequential_element_id(last_choice_in_group_id)


    def _execute_if(self, element: IfElement) -> Optional[str]:
        """Handles conditional branching. Returns next element ID or command."""
        logger.debug(f"Executing IfElement ID: {element.element_id}")
        condition_repr = "Condition Error"
        try:
            # Condition object should be stored directly now
            condition_repr = element.condition.representation
            condition = Condition.create(condition_repr.strip())
            condition_met = condition.check(self.game_state)
            logger.info(f"Condition '{condition_repr}' evaluated to: {condition_met}")
        except ValueError as e:
            logger.warning(f"Invalid condition '{condition_repr}' in IfElement {element.element_id}: {e}")
            self.ui.notify(f"Warning: Invalid condition found in story logic: {condition_repr}", "warning")
            # Skip entire IfElement if condition invalid
            return self._get_next_sequential_element_id(element.element_id)
        except Exception as e:
             logger.error(f"Error evaluating condition '{condition_repr}' for IfElement {element.element_id}: {e}", exc_info=True)
             self.ui.notify(f"Error evaluating condition: {condition_repr}", "error")
             return None # Halt execution

        # No state change just for branching, so no history snapshot here

        next_id = None
        if condition_met:
            logger.debug(f"Condition met. Entering if_block for {element.element_id}.")
            if element.if_block:
                next_id = element.if_block[0].element_id # Start of if block
                logger.debug(f"Next element is start of if_block: {next_id}")
            else:
                logger.debug(f"if_block for {element.element_id} is empty. Skipping.")
                next_id = self._get_next_sequential_element_id(element.element_id) # Skip empty block
        else: # Condition not met
            logger.debug(f"Condition not met. Checking else_block for {element.element_id}.")
            if element.else_block:
                next_id = element.else_block[0].element_id # Start of else block
                logger.debug(f"Next element is start of else_block: {next_id}")
            else:
                logger.debug(f"else_block for {element.element_id} is empty/missing. Skipping.")
                next_id = self._get_next_sequential_element_id(element.element_id) # Skip block (no else)

        return next_id


    # --- Save, Load, Undo ---

    def save_game(self):
        """Handles the save game process."""
        logger.info("Initiating save game process...")
        filename = self.ui.get_save_filename()
        if not filename:
            logger.info("Save cancelled by user.")
            self.ui.notify("Save cancelled.", "info")
            return

        logger.debug(f"Attempting to save to filename: {filename}")
        save_data = {
            "current_element_id": self.current_element_id,
            "game_state": self.game_state.to_dict(),
            # Save history carefully - might become large
            "history": self.history # Already list of (dict, str_id)
        }

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=4)
            logger.info(f"Game saved successfully to {filename}")
            self.ui.notify(f"Game saved to {filename}", "success")
        except Exception as e:
            logger.error(f"Error saving game to {filename}: {e}", exc_info=True)
            self.ui.notify(f"Error saving game: {e}", "error")

    def load_game(self) -> bool:
        """Handles the load game process. Returns True if successful."""
        logger.info("Initiating load game process...")
        try:
            save_dir = '.' # Or specify a saves subdirectory
            available_files = [f for f in os.listdir(save_dir) if f.lower().endswith('.json')]
            logger.debug(f"Found available save files: {available_files}")
        except OSError as e:
            logger.error(f"Error listing save directory '{save_dir}': {e}")
            available_files = []
            self.ui.notify("Could not access save directory.", "error")

        filename = self.ui.get_load_filename(available_files)
        if not filename:
            logger.info("Load cancelled by user.")
            self.ui.notify("Load cancelled.", "info")
            return False

        logger.debug(f"Attempting to load from filename: {filename}")
        try:
            filepath = os.path.join(save_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                save_data = json.load(f)

            # Basic validation
            if not isinstance(save_data, dict) or \
               "current_element_id" not in save_data or \
               "game_state" not in save_data or \
               "history" not in save_data:
                raise ValueError("Invalid save file format.")

            logger.debug("Save file format validated.")

            # Restore state
            loaded_state = GameState.from_dict(save_data["game_state"])
            loaded_element_id = save_data["current_element_id"]
            loaded_history = save_data["history"]

            # Validate the loaded element ID exists in the current map
            if loaded_element_id is not None and not self._get_element_by_id(loaded_element_id):
                 logger.warning(f"Saved element ID '{loaded_element_id}' not found in current script's element map. Save might be from incompatible script version.")
                 self.ui.notify(f"Warning: Save data might be incompatible with the current script version (Element ID '{loaded_element_id}' not found). Attempting to continue...", "warning")
                 # Decide recovery: Could try finding scene start, or just warn.
                 # For now, let's proceed but the next step might fail. A safer approach might reset ID.
                 # self.current_element_id = None # Or reset to start?

            # Commit the loaded state
            self.game_state = loaded_state
            self.current_element_id = loaded_element_id
            self.history = loaded_history

            logger.info(f"Game loaded successfully from {filename}. Current element: {self.current_element_id}. History depth: {len(self.history)}")
            self.ui.notify(f"Game loaded from {filename}", "success")
            return True

        except FileNotFoundError:
             logger.error(f"Save file '{filename}' not found.")
             self.ui.notify(f"Save file '{filename}' not found.", "error")
             return False
        except json.JSONDecodeError as e:
             logger.error(f"Error decoding JSON from save file '{filename}': {e}")
             self.ui.notify(f"Save file '{filename}' is corrupted or not valid JSON.", "error")
             return False
        except ValueError as e: # Catch our format validation error
             logger.error(f"Invalid save file format in '{filename}': {e}")
             self.ui.notify(f"Save file '{filename}' has an invalid format.", "error")
             return False
        except Exception as e:
            logger.error(f"Error loading game from {filename}: {e}", exc_info=True)
            self.ui.notify(f"Error loading game: {e}", "error")
            return False


    def undo(self):
        """Reverts the game state to the previous point in history."""
        logger.info("Attempting undo operation...")
        if len(self.history) <= 1: # Need at least the initial state and one action state
            logger.warning("Cannot undo: No previous state in history.")
            self.ui.notify("Cannot undo further.", "info")
            return

        try:
            # Remove the current state snapshot from history
            self.history.pop()
            logger.debug(f"Removed current state. History depth now: {len(self.history)}")
            # Get the previous state and the element ID that *led* to it
            previous_state_dict, element_id_that_led_to_this_state = self.history[-1] # Peek at the new top

            # Restore the game state
            self.game_state = GameState.from_dict(previous_state_dict)
            # Set the runner to execute the element *that caused* the now-current state
            self.current_element_id = element_id_that_led_to_this_state

            logger.info(f"Undo successful. Restored state. Next element to execute: {self.current_element_id}")

            # Validate the element ID still exists (optional but good practice)
            if self.current_element_id and not self._get_element_by_id(self.current_element_id):
                 logger.warning(f"Element ID '{self.current_element_id}' restored from history not found in current script map. Execution might halt.")
                 self.ui.notify("Warning: Story structure may have changed since this point was saved. Cannot guarantee correct continuation.", "warning")
                 # Consider halting by setting ID to None? Or let it fail on next loop?
                 # self.current_element_id = None

            self.ui.notify("Undo successful.", "success")

        except Exception as e:
            logger.error(f"Error during undo operation: {e}", exc_info=True)
            self.ui.notify(f"Error during undo: {e}", "error")
            # State might be inconsistent, consider halting
            self.current_element_id = None
