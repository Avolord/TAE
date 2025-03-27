from rich.panel import Panel
from rich.table import Table
from rich.box import ROUNDED
from rich.prompt import Prompt

from tae_engine.ui.rich_interface import BaseUI

class InventoryUI(BaseUI):
    """UI component for displaying inventory."""
    
    def show(self, character_name: str, header_subtitle: str = None, allow_use: bool = True) -> None:
        """
        Display inventory items.
        
        Args:
            character_name: The name of the character
            header_subtitle: Optional subtitle for the header
            allow_use: Whether to allow using items from the inventory
        """
        # Create the inventory table
        table = Table(title=f"{character_name}'s Inventory")
        table.add_column("#", style="dim")
        table.add_column("Item", style="bold")
        table.add_column("Quantity", justify="right")
        
        items = list(self.game_state.inventory.items())
        
        for i, (item_name, quantity) in enumerate(items, 1):
            table.add_row(str(i), item_name, str(quantity))
        
        inventory_panel = Panel(table, box=ROUNDED)
        
        # Display the UI
        self.wrap_in_main_box(inventory_panel, f"{character_name}'s Inventory", header_subtitle)
        
        # Show instructions
        if allow_use and items:
            self.console.print("Enter a number to use/examine an item, or 'c' to continue")
        else:
            self.console.print("Press 'c' to continue")
        
        while True:
            # Get user input
            choice = self.get_input("", ["c"])
            
            # Check if it's continue
            if choice.lower() == 'c':
                return
            
            # Default actions are handled by get_input
            
            # Handle item use/examination
            if allow_use and items:
                try:
                    item_idx = int(choice) - 1
                    if 0 <= item_idx < len(items):
                        item_name = items[item_idx][0]
                        self.console.print(f"You examine the {item_name}.")
                        # Here you would typically call a function to use the item
                        # based on its type/properties
                        Prompt.ask("Press Enter to continue", default="")
                        # Redraw UI
                        self.wrap_in_main_box(inventory_panel, f"{character_name}'s Inventory", header_subtitle)
                    else:
                        self.console.print("Invalid item number.")
                        Prompt.ask("Press Enter to continue", default="")
                        self.wrap_in_main_box(inventory_panel, f"{character_name}'s Inventory", header_subtitle)
                except ValueError:
                    # Not a number, probably a default action
                    pass