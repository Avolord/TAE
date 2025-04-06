# main.py
import argparse
import sys
import os
import traceback
from typing import List

# Add project root to path if necessary (adjust based on your structure)
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- Engine Imports ---
from tae_engine.tales_lexer import TalesLexer
from tae_engine.tales_parser import TalesParser, SceneElement
from tae_engine.tales_runner import TalesRunner # Import the new runner
from tae_engine.ui_interface import UIInterface # Import the interface definition

# --- UI Imports ---
# Import your chosen UI implementation
from tae_engine.ui.console_ui_placeholder import ConsoleUIPlaceholder

# --- Basic Console for Startup Messages ---
# Use Rich Console only for initial messages if UI takes over completely
# Otherwise, the UI's console might be sufficient.
from rich.console import Console as RichConsole


def main():
    parser = argparse.ArgumentParser(
        description="Run a TALES script using the Text Adventure Engine"
    )
    parser.add_argument("script", help="Path to the TALES script file")
    # --start argument is less relevant now as saves handle position,
    # but could be kept for starting a new game at a specific scene.
    # parser.add_argument("--start", help="Name of the scene to start a new game from")
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug logging to file (tae_runner.log)"
    )
    args = parser.parse_args()

    # Use Rich Console for startup messages before UI takes over
    startup_console = RichConsole(highlight=True)

    # --- Setup Logging Level based on Debug Flag ---
    # The logger is configured in runner.py, but we can adjust level here if needed
    # (Alternatively, pass debug flag to runner/logger setup)
    # import logging
    # log_level = logging.DEBUG if args.debug else logging.INFO
    # logging.getLogger('TalesRunner').setLevel(log_level)
    # Note: Runner currently defaults to DEBUG, which is fine.

    try:
        # 1. Load Script
        startup_console.print(f"[blue]Loading script:[/blue] {args.script}")
        if not os.path.exists(args.script):
             startup_console.print(f"[bold red]Error:[/bold red] Script file not found: {args.script}")
             sys.exit(1) # Exit if script not found
        with open(args.script, "r", encoding="utf-8") as file:
            tale_script = file.read()

        # 2. Lex and Parse
        startup_console.print(f"[blue]Lexing:[/blue] {args.script}...")
        tokenized_lines = TalesLexer.tokenize(tale_script) # Might raise ValueError

        startup_console.print(f"[blue]Parsing:[/blue] {args.script}...")
        parser = TalesParser(tokenized_lines)
        ast: List[SceneElement] = parser.parse() # Might raise ValueError

        if not ast:
            startup_console.print("[bold red]Error: Script parsed into an empty AST. Cannot run.[/bold red]")
            sys.exit(1) # Exit if AST is empty
        startup_console.print(f"[green]Parsed {len(ast)} scene(s).[/green]")

        # 3. Initialize UI
        # Replace ConsoleUIPlaceholder with a different implementation later
        # The UI implementation itself might handle console clearing etc.
        ui: UIInterface = ConsoleUIPlaceholder()
        startup_console.print("[blue]UI Initialized.[/blue]")

        # 4. Initialize and Run the Runner
        startup_console.print("[bold green]Initializing Tales Runner...[/bold green]\n")
        # The runner now handles GameState initialization internally
        runner = TalesRunner(ast, ui) # Might raise errors during init
        runner.run() # Start the main execution loop

    except FileNotFoundError: # Should be caught earlier, but as fallback
        startup_console.print(f"[bold red]Error:[/bold red] Script file not found: {args.script}")
        sys.exit(1)
    except ValueError as e: # Catch parsing/lexing ValueErrors
        startup_console.print(f"\n[bold red]An error occurred during setup:[/bold red]\n{e}")
        # Log the traceback for detailed debugging if needed
        # logger.error("Setup Error", exc_info=True) # Requires logger setup here
        traceback.print_exc() # Print traceback to console for setup errors
        sys.exit(1)
    except Exception as e: # Catch unexpected errors during setup
        startup_console.print(f"\n[bold red]An unexpected error occurred during setup:[/bold red]\n{e}")
        # logger.critical("Unexpected Setup Error", exc_info=True)
        traceback.print_exc()
        sys.exit(1)

    # Optional: Message indicating clean exit
    # print("\nApplication finished.")


if __name__ == "__main__":
    main()
