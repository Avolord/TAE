from typing import List, Dict, Any
from rich.panel import Panel
from rich.table import Table
from rich.box import ROUNDED
from rich.prompt import Prompt

from tae_engine.ui.rich_interface import BaseUI

class ShopUI(BaseUI):
    """UI component for displaying a shop."""
    
    def show(self, shop_name: str, items: List[Dict[str, Any]], currency_name: str = "gold", header_subtitle: str = None) -> None:
        """
        Display a shop with items to buy.
        
        Args:
            shop_name: The name of the shop
            items: List of item dictionaries, each with 'name', 'price', 'description', and optionally 'condition'
            currency_name: The name of the currency
            header_subtitle: Optional subtitle for the header
        """
        # Filter items that don't meet their conditions
        valid_items = []
        for item in items:
            condition = item.get('condition', lambda state: True)
            if callable(condition) and condition(self.game_state):
                valid_items.append(item)
        
        while True:
            # Get player's currency
            currency = self.game_state.stats.get(currency_name, 0)
            
            # Create the shop table
            table = Table(title=f"Available Items (You have {currency} {currency_name})")
            table.add_column("#", style="dim")
            table.add_column("Item", style="bold")
            table.add_column("Price", justify="right")
            table.add_column("Description")
            
            for i, item in enumerate(valid_items, 1):
                table.add_row(
                    str(i),
                    item['name'],
                    f"{item['price']} {currency_name}",
                    item['description']
                )
            
            shop_panel = Panel(table, box=ROUNDED)
            
            # Display the UI
            self.wrap_in_main_box(shop_panel, shop_name, header_subtitle)
            
            # Get user input
            self.console.print("Enter the number to buy an item (or 'x' to exit)")
            choice = self.get_input("Shop", ["x"])
            
            # Check if it's exit
            if choice.lower() == 'x':
                return
            
            # Check if it's a default action
            if choice in self.default_actions:
                continue
            
            # Try to handle purchase
            try:
                item_idx = int(choice) - 1
                if 0 <= item_idx < len(valid_items):
                    item = valid_items[item_idx]
                    
                    if currency >= item['price']:
                        # Update currency and inventory
                        self.game_state.stats[currency_name] -= item['price']
                        self.game_state.add_to_inventory(item['name'], 1)
                        
                        self.console.print(f"You bought {item['name']} for {item['price']} {currency_name}.")
                        Prompt.ask("Press Enter to continue", default="")
                    else:
                        self.console.print(f"Not enough {currency_name} to buy {item['name']}.")
                        Prompt.ask("Press Enter to continue", default="")
                else:
                    self.console.print("Invalid item number.")
                    Prompt.ask("Press Enter to continue", default="")
            except ValueError:
                self.console.print("Please enter a number or 'x' to exit.")
                Prompt.ask("Press Enter to continue", default="")