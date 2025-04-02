# tales_parser.py
from dataclasses import dataclass, field
from tae_engine.tales_lexer import TokenType, TalesLexer
from typing import Dict, List, Tuple, Any, Optional, Union

# --- Base Class ---
class Element:
    """Base class marker for type hinting AST nodes."""
    pass

# --- Concrete Elements as Dataclasses ---

@dataclass
class SceneElement(Element):
    """Represents a scene definition."""
    scene_name: str
    content: List[Element] = field(default_factory=list)
    # ... (repr method)

@dataclass
class DialogueElement(Element):
    """Represents a dialogue line with optional effects."""
    speaker: str
    dialogue_text: str
    # Store raw effect strings
    effects: List[str] = field(default_factory=list)

    def __repr__(self) -> str:
        fx_info = f", effects={self.effects}" if self.effects else ""
        return f"Dialogue(speaker='{self.speaker}', text='{self.dialogue_text}'{fx_info})"

@dataclass
class ChoiceElement(Element):
    """Represents a choice line with text, optional transition, condition, and effects."""
    level: int # Number of asterisks
    text: str
    transition: Optional[str] = None
    # Store raw condition string (content inside {if ...})
    condition_str: Optional[str] = None
    # Store raw effect strings
    effects: List[str] = field(default_factory=list)

    def __repr__(self) -> str:
        parts = [f"Choice(level={self.level}, text='{self.text}'"]
        if self.transition:
            parts.append(f" -> {self.transition}")
        if self.condition_str:
            parts.append(f", condition='{self.condition_str}'")
        if self.effects:
            parts.append(f", effects={self.effects}")
        parts.append(")")
        return "".join(parts)

# --- IfElement and Condition/Effect placeholders remain the same for now ---
@dataclass
class Condition(Element): # Placeholder for IfElement's condition
    representation: str
    def __repr__(self): return f"Condition({self.representation})"

@dataclass
class IfElement(Element):
    condition: Condition
    if_block: List[Element] = field(default_factory=list)
    else_block: Optional[List[Element]] = None
    # ... (repr method)

# --- Parser Class ---

class TalesParser:
    def __init__(self, token_lines: Dict[int, List[Tuple[TokenType, str]]]):
        self.token_lines = token_lines
        self.ast: List[SceneElement] = []
        self._lines = list(self.token_lines.values())
        self._line_numbers = list(self.token_lines.keys())

    # --- Bracket Parsing Helper ---
    def _parse_bracket_content(
        self, tokens: List[Tuple[TokenType, str]], open_bracket_index: int
    ) -> Tuple[str, int]:
        """
        Parses content within matching curly brackets {}.

        Args:
            tokens: The list of tokens for the current line.
            open_bracket_index: The index of the opening bracket token '{'.

        Returns:
            A tuple containing:
            - The concatenated string content inside the brackets.
            - The index of the token immediately AFTER the closing bracket.

        Raises:
            ValueError: If brackets are unbalanced or EOF is reached unexpectedly.
        """
        if tokens[open_bracket_index][0] != TokenType.OPEN_BRACKET:
            raise ValueError("Internal Error: _parse_bracket_content called without OPEN_BRACKET.")

        level = 1
        content_parts = []
        pos = open_bracket_index + 1
        line_len = len(tokens)

        while pos < line_len:
            token_type, token_value = tokens[pos]

            if token_type == TokenType.OPEN_BRACKET:
                level += 1
            elif token_type == TokenType.CLOSE_BRACKET:
                level -= 1
                if level == 0:
                    # Found the matching closing bracket
                    # Join parts with space, trim leading/trailing whitespace
                    return "".join(content_parts).strip(), pos + 1
            # Only append if we are not the final closing bracket
            if level > 0:
                 content_parts.append(token_value)

            pos += 1

        # If loop finishes, brackets were unbalanced
        raise ValueError("Unbalanced curly brackets or missing closing bracket '}'.")


    # --- Matching Helper Methods ---

    def _match_scene(self, tokens: List[Tuple[TokenType, str]]) -> Optional[SceneElement]:
        # ... (previous implementation) ...
        if (len(tokens) >= 2 and tokens[0][0] == TokenType.SCENE and
                tokens[1][0] == TokenType.TEXT):
            scene_name = tokens[1][1]
            if len(tokens) > 2:
                raise ValueError(f"Unexpected token '{tokens[2][1]}' after scene name '{scene_name}'.")
            return SceneElement(scene_name=scene_name)
        return None

    def _match_dialogue(self, tokens: List[Tuple[TokenType, str]]) -> Optional[DialogueElement]:
        """Attempts to parse a DialogueElement, including effects."""
        if not (len(tokens) >= 4 and
                tokens[0][0] == TokenType.DIALOGUE and
                tokens[1][0] == TokenType.TEXT and # Speaker
                tokens[2][0] == TokenType.SEPARATOR and
                tokens[3][0] == TokenType.TEXT): # Dialogue content
            # Raise error only if it *starts* like dialogue but doesn't match basic form
            if len(tokens) > 0 and tokens[0][0] == TokenType.DIALOGUE:
                raise ValueError(f"Invalid dialogue format. Expected '> Speaker: Text ...', got: {tokens}")
            return None # Doesn't start with dialogue pattern

        speaker = tokens[1][1]
        dialogue_text = tokens[3][1]
        effects = []
        pos = 4 # Start checking for effects after the main dialogue text

        while pos < len(tokens):
            token_type = tokens[pos][0]
            if token_type == TokenType.OPEN_BRACKET:
                try:
                    # Effects are just the raw string content inside {}
                    effect_str, next_pos = self._parse_bracket_content(tokens, pos)
                    effects.append(effect_str)
                    pos = next_pos # Move position past the parsed effect block
                except ValueError as e:
                    # Re-raise bracket error with more context
                    raise ValueError(f"Error parsing effect brackets in dialogue: {e}") from e
            else:
                # If we find anything other than an opening bracket here, it's invalid
                raise ValueError(f"Unexpected token '{tokens[pos][1]}' after dialogue text or effects.")

        # If loop finishes, we've consumed all tokens correctly
        return DialogueElement(speaker=speaker, dialogue_text=dialogue_text, effects=effects)


    def _match_choice(self, tokens: List[Tuple[TokenType, str]]) -> Optional[ChoiceElement]:
        """
        Attempts to parse a ChoiceElement.
        The first {} block is the condition (can be empty).
        Subsequent {} blocks are effects.
        """
        if not tokens or tokens[0][0] != TokenType.CHOICE:
            return None

        level = len(tokens[0][1])
        pos = 1

        if pos >= len(tokens) or tokens[pos][0] != TokenType.TEXT:
            raise ValueError(f"Missing text after choice marker '{tokens[0][1]}'.")
        choice_text = tokens[pos][1]
        pos += 1

        # --- Initialize optional parts ---
        # Use different local variable names to avoid confusion with the loop's scope
        parsed_destination: Optional[str] = None
        parsed_condition_str: Optional[str] = None # Initialize condition as None
        parsed_effects: List[str] = []
        found_condition_block = False # Flag to track if we've processed the first {}

        while pos < len(tokens):
            token_type, token_value = tokens[pos]

            if token_type == TokenType.TRANSITION:
                if parsed_destination is not None: # Check the variable holding the result
                    raise ValueError("Multiple transitions '->' found for the same choice.")
                pos += 1
                if pos >= len(tokens) or tokens[pos][0] != TokenType.TEXT:
                    raise ValueError("Missing destination scene name after transition '->'.")
                parsed_destination = tokens[pos][1] # Assign to the result variable
                pos += 1
                continue

            elif token_type == TokenType.OPEN_BRACKET:
                try:
                    bracket_content, next_pos = self._parse_bracket_content(tokens, pos)

                    if not found_condition_block:
                        # This is the FIRST bracket block - it's the condition.
                        # Assign its content (even if empty) to our result variable.
                        parsed_condition_str = bracket_content
                        found_condition_block = True # Mark condition as processed
                    else:
                        # Subsequent bracket blocks are effects
                        parsed_effects.append(bracket_content) # Add to the result list

                    pos = next_pos # Move position past the parsed block
                except ValueError as e:
                    raise ValueError(f"Error parsing brackets in choice: {e}") from e
                continue

            else:
                raise ValueError(f"Unexpected token '{token_value}' in choice definition.")

        # --- Create and return the element using the parsed results ---
        return ChoiceElement(
            level=level,
            text=choice_text,
            transition=parsed_destination,
            condition_str=parsed_condition_str, # Use the variable populated in the loop
            effects=parsed_effects # Use the list populated in the loop
        )

    # --- Condition/Effect Parsing Helpers (Placeholders for IfElement) ---
    def _parse_condition(self, condition_tokens: List[Tuple[TokenType, str]]) -> Condition:
         # This is used by IfElement, keep placeholder logic for now
         # ... (previous placeholder implementation) ...
         rep = "".join(t[1] for t in condition_tokens)
         return Condition(representation=rep)


    def parse(self) -> List[SceneElement]:
        # ... (previous implementation, calls _match_scene and parse_scene) ...
        self.ast = []
        current_line_idx = 0
        num_lines = len(self._lines)

        while current_line_idx < num_lines:
            current_tokens = self._lines[current_line_idx]
            current_file_line_num = self._line_numbers[current_line_idx]

            if not current_tokens:
                current_line_idx += 1
                continue

            try:
                scene_element = self._match_scene(current_tokens)
                if scene_element:
                    next_line_idx, populated_scene_element = self.parse_scene(
                        scene_element, current_line_idx + 1
                    )
                    self.ast.append(populated_scene_element)
                    current_line_idx = next_line_idx
                else:
                    raise ValueError(f"Expected '@scene' definition or empty line, but found: {current_tokens[0][1]}")
            except ValueError as e:
                raise ValueError(f"Parser Error near line {current_file_line_num}: {e}") from e
            except NotImplementedError as e:
                raise NotImplementedError(f"Parsing feature not implemented near line {current_file_line_num}: {e}") from e

        return self.ast


    def parse_scene(
        self, scene_element: SceneElement, start_line_idx: int
    ) -> Tuple[int, SceneElement]:
        # ... (previous implementation, calls _match_dialogue, _match_choice, _parse_if_block) ...
        current_line_idx = start_line_idx
        num_lines = len(self._lines)

        while current_line_idx < num_lines:
            # Ensure index is valid before accessing
            if current_line_idx >= len(self._lines): break

            current_tokens = self._lines[current_line_idx]
            current_file_line_num = self._line_numbers[current_line_idx]

            if not current_tokens:
                current_line_idx += 1
                continue

            if current_tokens[0][0] == TokenType.SCENE:
                return current_line_idx, scene_element

            first_token_type = current_tokens[0][0]
            parsed_element: Optional[Element] = None
            lines_consumed_this_iteration = 0

            try:
                if first_token_type == TokenType.IF:
                    parsed_element, lines_consumed_this_iteration = self._parse_if_block(current_line_idx)
                elif first_token_type == TokenType.DIALOGUE:
                    parsed_element = self._match_dialogue(current_tokens)
                    if parsed_element: lines_consumed_this_iteration = 1
                elif first_token_type == TokenType.CHOICE:
                    parsed_element = self._match_choice(current_tokens)
                    if parsed_element: lines_consumed_this_iteration = 1
                elif first_token_type in (TokenType.ELSE, TokenType.ENDIF):
                     raise ValueError(f"Unexpected '{current_tokens[0][1]}' outside of an '@if' block")

                if parsed_element:
                    scene_element.content.append(parsed_element)
                    current_line_idx += lines_consumed_this_iteration
                elif first_token_type == TokenType.IF: # Handle case where if block parsing failed/skipped
                     if lines_consumed_this_iteration == 0: lines_consumed_this_iteration = 1
                     current_line_idx += lines_consumed_this_iteration
                else:
                    raise ValueError(f"Unexpected token sequence starting with {current_tokens[0][1]}")

            except ValueError as e:
                 raise ValueError(f"Parser Error in scene '{scene_element.scene_name}' near line {current_file_line_num}: {e}") from e
            except NotImplementedError as e:
                 print(f"Warning: Skipping unimplemented feature near line {current_file_line_num}")
                 current_line_idx += 1

        return current_line_idx, scene_element


    def _parse_if_block(self, start_line_idx: int) -> Tuple[IfElement, int]:
        # ... (previous implementation, calls _match_dialogue, _match_choice internally) ...
        # Ensure the internal loop calls the correct matchers
        num_lines = len(self._lines)
        initial_file_line_num = self._line_numbers[start_line_idx]
        if_line_tokens = self._lines[start_line_idx]

        if not if_line_tokens or if_line_tokens[0][0] != TokenType.IF:
            raise ValueError("Internal Parser Error: _parse_if_block called on non-@if line.")
        if len(if_line_tokens) < 2:
            raise ValueError(f"Missing condition after @if near line {initial_file_line_num}")

        condition = self._parse_condition(if_line_tokens[1:])
        if_element = IfElement(condition=condition)

        current_line_idx = start_line_idx + 1
        lines_consumed = 1
        parsing_if_branch = True
        active_block = if_element.if_block

        while current_line_idx < num_lines:
            # Ensure index is valid before accessing
            if current_line_idx >= len(self._lines):
                 raise ValueError(f"Unterminated '@if' block starting near line {initial_file_line_num}")

            current_tokens = self._lines[current_line_idx]
            current_file_line_num = self._line_numbers[current_line_idx]
            lines_consumed += 1

            if not current_tokens:
                current_line_idx += 1
                continue

            first_token_type = current_tokens[0][0]

            if first_token_type == TokenType.ELSE:
                # ... (else handling) ...
                if not parsing_if_branch: raise ValueError(f"Unexpected '@else' near line {current_file_line_num}")
                if len(current_tokens) > 1: raise ValueError(f"Unexpected tokens after '@else' near line {current_file_line_num}")
                parsing_if_branch = False
                if_element.else_block = []
                active_block = if_element.else_block
                current_line_idx += 1
                continue

            elif first_token_type == TokenType.ENDIF:
                # ... (endif handling) ...
                if len(current_tokens) > 1: raise ValueError(f"Unexpected tokens after '@endif' near line {current_file_line_num}")
                return if_element, lines_consumed

            parsed_element: Optional[Element] = None
            lines_consumed_by_nested = 0

            try:
                if first_token_type == TokenType.IF:
                    parsed_element, lines_consumed_by_nested = self._parse_if_block(current_line_idx)
                elif first_token_type == TokenType.DIALOGUE:
                    parsed_element = self._match_dialogue(current_tokens)
                    if parsed_element: lines_consumed_by_nested = 1
                elif first_token_type == TokenType.CHOICE:
                    parsed_element = self._match_choice(current_tokens)
                    if parsed_element: lines_consumed_by_nested = 1
                elif first_token_type == TokenType.SCENE:
                     raise ValueError(f"Cannot define a scene inside an '@if' block near line {current_file_line_num}")

                if parsed_element:
                    active_block.append(parsed_element)
                    current_line_idx += lines_consumed_by_nested
                    lines_consumed += lines_consumed_by_nested - 1
                elif first_token_type == TokenType.IF: # Handle case where nested if wasn't fully parsed
                     if lines_consumed_by_nested == 0: lines_consumed_by_nested = 1
                     current_line_idx += lines_consumed_by_nested
                     lines_consumed += lines_consumed_by_nested - 1
                else:
                    raise ValueError(f"Unexpected token sequence within @if block near line {current_file_line_num}: {current_tokens[0]}")

            except ValueError as e:
                 raise ValueError(f"Parser Error within @if block near line {current_file_line_num}: {e}") from e
            except NotImplementedError as e:
                 print(f"Warning: Skipping unimplemented feature within @if block near line {current_file_line_num}")
                 current_line_idx += 1

        raise ValueError(f"Unterminated '@if' block starting near line {initial_file_line_num}")


# --- Main Execution Block ---
# ... (Keep the __main__ block as it was) ...
if __name__ == "__main__":
    # filename = "test.tales"
    filename = "test.tales" # Use the complex test
    try:
        with open(filename, "r", encoding="utf-8") as file:
            tale_script = file.read()

        print(f"--- Lexing {filename} ---")
        tokenized_lines = TalesLexer.tokenize(tale_script)
        # Optional: Print tokens for debugging
        # for i, line_tokens in tokenized_lines.items():
        #     print(f"Line {i}: {line_tokens}")


        print(f"\n--- Parsing {filename} ---")
        parser = TalesParser(tokenized_lines)
        parsed_ast = parser.parse()

        print("\n--- Parsed Structure (AST) ---")
        if not parsed_ast:
            print("Parsing resulted in an empty structure.")
        for scene in parsed_ast:
            print(scene)
            # Optional: Print content of each scene for more detail
            # for element in scene.content:
            #     print(f"  {element}")


    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")
    except ValueError as e:
        print(f"\n--- PARSER/LEXER ERROR ---")
        print(e)
        # Optional: Add traceback for ValueErrors during debugging
        # import traceback
        # traceback.print_exc()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
