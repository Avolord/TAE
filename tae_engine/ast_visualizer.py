# ast_visualizer.py (or add to main.py/tales_parser.py)

from typing import List, Union, Optional
import sys

from tae_engine.tales_lexer import TalesLexer
from tae_engine.tales_parser import TalesParser

# Make sure these imports work based on where you place the code
# You might need to adjust relative paths if placed outside the main script
try:
    from tae_engine.tales_parser import (
        Element,
        SceneElement,
        DialogueElement,
        ChoiceElement,
        IfElement,
        Condition,
    )
except ImportError:
    # Fallback if running from a different location or structure changes
    print(
        "Warning: Could not import TAE elements directly."
        " Visualization might be limited.",
        file=sys.stderr,
    )
    # Define dummy classes if needed for type hinting, though not ideal
    class Element:
        pass

    class SceneElement(Element):
        scene_name: str
        content: List[Element]

    class DialogueElement(Element):
        speaker: str
        dialogue_text: str
        effects: List[str]

    class ChoiceElement(Element):
        level: int
        text: str
        transition: Optional[str]
        condition_str: Optional[str]
        effects: List[str]

    class IfElement(Element):
        condition: "Condition"
        if_block: List[Element]
        else_block: Optional[List[Element]]

    class Condition(Element):
        representation: str


# Emojis for cuteness! 💖
NODE_EMOJIS = {
    "Scene": "🎬",
    "Dialogue": "💬",
    "Choice": "👉",
    "If": "🤔",
    "Condition": "❓",
    "Effect": "✨",
    "Transition": "🚀",
    "Block": "📦",
}

# Tree drawing characters
T_BRANCH = "├── "
L_BRANCH = "└── "
V_LINE = "│   "
EMPTY = "    "


def _format_details(element: Element) -> str:
    """Formats the specific details for each element type."""
    details = []
    if isinstance(element, DialogueElement):
        details.append(f"🗣️ Speaker: '{element.speaker}'")
        details.append(f"📜 Text: '{element.dialogue_text[:40]}...'")
        if element.effects:
            details.append(
                f"{NODE_EMOJIS['Effect']} Effects: {element.effects}"
            )
    elif isinstance(element, ChoiceElement):
        details.append(f"⭐ Level: {element.level}")
        details.append(f"📜 Text: '{element.text[:40]}...'")
        if element.condition_str:
            details.append(
                f"{NODE_EMOJIS['Condition']} Condition: '{element.condition_str}'"
            )
        if element.transition:
            details.append(
                f"{NODE_EMOJIS['Transition']} Transition: -> {element.transition}"
            )
        if element.effects:
            details.append(
                f"{NODE_EMOJIS['Effect']} Effects: {element.effects}"
            )
    elif isinstance(element, IfElement):
        details.append(
            f"{NODE_EMOJIS['Condition']} Condition: '{element.condition.representation}'"
        )
    elif isinstance(element, SceneElement):
        # Scene name is already part of the main line
        pass
    return " | ".join(details)


def _visualize_node(
    element: Element, prefix: str = "", is_last: bool = True
):
    """Recursively prints a node and its children."""
    connector = L_BRANCH if is_last else T_BRANCH

    node_type = type(element).__name__.replace("Element", "")
    emoji = NODE_EMOJIS.get(node_type, "❓")
    name = ""
    children = []
    extra_prefix_if = ""
    extra_prefix_else = ""

    if isinstance(element, SceneElement):
        name = f"'{element.scene_name}'"
        children = element.content
    elif isinstance(element, DialogueElement):
        name = f"'{element.speaker}'" # Show speaker for dialogue
    elif isinstance(element, ChoiceElement):
        name = f"'{element.text[:30]}...'" # Show start of choice text
    elif isinstance(element, IfElement):
        name = f"Condition: {element.condition.representation}"
        # Special handling for if/else blocks
        print(f"{prefix}{connector}{emoji} If {name}")
        child_prefix = prefix + (EMPTY if is_last else V_LINE)

        # Print 'if' block
        print(f"{child_prefix}├─ {NODE_EMOJIS['Block']} If Block:")
        block_prefix = child_prefix + "│   "
        for i, child in enumerate(element.if_block):
            _visualize_node(
                child,
                block_prefix,
                i == len(element.if_block) - 1
                and not element.else_block,
            )

        # Print 'else' block if it exists
        if element.else_block:
            print(f"{child_prefix}└─ {NODE_EMOJIS['Block']} Else Block:")
            block_prefix = child_prefix + "    "
            for i, child in enumerate(element.else_block):
                _visualize_node(
                    child, block_prefix, i == len(element.else_block) - 1
                )
        return # Handled children internally

    details = _format_details(element)
    print(f"{prefix}{connector}{emoji} {node_type} {name}")
    if details:
         print(f"{prefix}{EMPTY if is_last else V_LINE}   ({details})")


    child_prefix = prefix + (EMPTY if is_last else V_LINE)
    for i, child in enumerate(children):
        _visualize_node(child, child_prefix, i == len(children) - 1)


def visualize_ast(ast: List[Element]):
    """Prints a cute visualization of the parsed TALES AST."""
    print("🌳 TALES Abstract Syntax Tree 🌳")
    print("================================")
    if not ast:
        print("(No scenes found in the AST)")
        return

    for i, scene in enumerate(ast):
        if isinstance(scene, SceneElement):
            _visualize_node(scene, "", i == len(ast) - 1)
        else:
            # Should ideally only be SceneElements at the top level
            print(f"❓ Unexpected Top-Level Element: {type(scene).__name__}")
            _visualize_node(scene, "", i == len(ast) - 1)
    print("================================")


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
            visualize_ast(parsed_ast)
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
