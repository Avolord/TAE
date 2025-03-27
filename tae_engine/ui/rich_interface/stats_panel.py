from rich.panel import Panel
from rich.table import Table
from rich.box import ROUNDED
from rich.prompt import Prompt

from tae_engine.ui.rich_interface import BaseUI

class StatsPanel(BaseUI):
    """UI component for displaying character stats."""
    
    def show(self, character_name: str, header_subtitle: str = None) -> None:
        """
        Display character stats.
        
        Args:
            character_name: The name of the character
            header_subtitle: Optional subtitle for the header
        """
        # Create the stats table
        table = Table(title=f"{character_name}'s Stats")
        table.add_column("Stat", style="bold")
        table.add_column("Value", justify="right")
        
        for stat_name, stat_value in self.game_state.stats.items():
            table.add_row(stat_name, str(stat_value))
        
        stats_panel = Panel(table, box=ROUNDED)
        
        # Display the UI
        self.wrap_in_main_box(stats_panel, f"{character_name}'s Stats", header_subtitle)
        
        # Wait for any key to continue
        self.console.print("Press 'c' to continue")
        while True:
            choice = self.get_input("", ["c"])
            
            # Check if it's continue
            if choice.lower() == 'c':
                return
            
            # Default actions are handled by get_input