from rich.console import Console
from rich.panel import Panel
from rich.align import Align
from rich.table import Table
from rich.box import ROUNDED

from tae_engine.game_state import GameState
from tae_engine.choice import Choice, ChoiceSet, choice_with_effect, choice_with_condition
from tae_engine.ui.rich_interface import (
    ChoiceBox,
    DialogueBox,
    ShopUI,
    StatsPanel,
    InventoryUI
)

import random
import time

class BattleSystem:
    """Handles battle mechanics for the goblin fighting game."""
    
    def __init__(self, game_state: GameState):
        self.game_state = game_state
        self.console = Console()
    
    def initialize_player(self):
        """Set up initial player stats."""
        self.game_state.update_stat("health", 100)
        self.game_state.update_stat("max_health", 100)
        self.game_state.update_stat("attack", 15)
        self.game_state.update_stat("defense", 5)
        self.game_state.update_stat("speed", 10)
        self.game_state.update_stat("gold", 50)
        self.game_state.update_stat("goblins_defeated", 0)
        
        # Add starting items
        self.game_state.add_to_inventory("Health Potion", 2)
    
    def create_goblin(self, difficulty: int = 1):
        """Create a goblin with stats based on difficulty."""
        # Scale goblin stats based on difficulty
        health = 30 + (difficulty * 10)
        attack = 8 + (difficulty * 2)
        defense = 2 + (difficulty)
        speed = 5 + (difficulty)
        
        # Store goblin stats in game variables
        self.game_state.set_variable("goblin_health", health)
        self.game_state.set_variable("goblin_max_health", health)
        self.game_state.set_variable("goblin_attack", attack)
        self.game_state.set_variable("goblin_defense", defense)
        self.game_state.set_variable("goblin_speed", speed)
        self.game_state.set_variable("goblin_difficulty", difficulty)
        
        # Create a goblin name
        goblin_types = ["Scrawny", "Fierce", "Sneaky", "Brutish", "Cunning", "Savage"]
        goblin_name = f"{random.choice(goblin_types)} Goblin"
        if difficulty > 3:
            goblin_name = f"Elite {goblin_name}"
        if difficulty > 5:
            goblin_name = f"Champion {goblin_name}"
            
        self.game_state.set_variable("goblin_name", goblin_name)
        
        return goblin_name
    
    def player_attack(self):
        """Player attacks the goblin."""
        player_attack = self.game_state.stats["attack"]
        goblin_defense = self.game_state.get_variable("goblin_defense")
        
        # Calculate base damage
        damage = max(1, player_attack - goblin_defense)
        
        # Chance for critical hit (20% chance)
        if random.random() < 0.2:
            damage = int(damage * 1.5)
            self.console.print("[bold yellow]Critical hit![/bold yellow]")
        
        # Apply damage to goblin
        goblin_health = self.game_state.get_variable("goblin_health")
        goblin_health = max(0, goblin_health - damage)
        self.game_state.set_variable("goblin_health", goblin_health)
        
        goblin_name = self.game_state.get_variable("goblin_name")
        self.console.print(f"You attack the {goblin_name} for [bold red]{damage}[/bold red] damage!")
        
        # Check if goblin is defeated
        if goblin_health <= 0:
            return True
        return False
    
    def goblin_attack(self):
        """Goblin attacks the player."""
        goblin_attack = self.game_state.get_variable("goblin_attack")
        player_defense = self.game_state.stats["defense"]
        
        # Calculate base damage
        damage = max(1, goblin_attack - player_defense)
        
        # Apply damage to player
        player_health = self.game_state.stats["health"]
        player_health = max(0, player_health - damage)
        self.game_state.update_stat("health", player_health)
        
        goblin_name = self.game_state.get_variable("goblin_name")
        self.console.print(f"The {goblin_name} attacks you for [bold red]{damage}[/bold red] damage!")
        
        # Check if player is defeated
        if player_health <= 0:
            return True
        return False
    
    def display_battle_ui(self):
        """Display the battle UI showing health of both combatants."""
        goblin_name = self.game_state.get_variable("goblin_name")
        goblin_health = self.game_state.get_variable("goblin_health")
        goblin_max_health = self.game_state.get_variable("goblin_max_health")
        
        player_health = self.game_state.stats["health"]
        player_max_health = self.game_state.stats["max_health"]
        
        # Create health displays
        goblin_health_percent = int((goblin_health / goblin_max_health) * 20)
        goblin_health_bar = f"[{'#' * goblin_health_percent}{' ' * (20 - goblin_health_percent)}]"
        
        player_health_percent = int((player_health / player_max_health) * 20)
        player_health_bar = f"[{'#' * player_health_percent}{' ' * (20 - player_health_percent)}]"
        
        # Display battle status
        battle_table = Table(box=ROUNDED, expand=True)
        battle_table.add_column("Combatant", style="bold")
        battle_table.add_column("Health")
        battle_table.add_column("Health Bar")
        
        battle_table.add_row(
            goblin_name, 
            f"{goblin_health}/{goblin_max_health}", 
            f"[{'red' if goblin_health_percent < 5 else 'yellow' if goblin_health_percent < 10 else 'green'}]{goblin_health_bar}[/]"
        )
        
        battle_table.add_row(
            "You", 
            f"{player_health}/{player_max_health}", 
            f"[{'red' if player_health_percent < 5 else 'yellow' if player_health_percent < 10 else 'green'}]{player_health_bar}[/]"
        )
        
        battle_panel = Panel(
            battle_table,
            title="Battle Status",
            border_style="bright_blue"
        )
        
        self.console.print(battle_panel)

def goblin_battle_game():
    console = Console()
    game_state = GameState()
    battle_system = BattleSystem(game_state)
    
    # Initialize UI elements
    choice_ui = ChoiceBox(console)
    choice_ui.game_state = game_state
    
    dialogue_ui = DialogueBox(console)
    dialogue_ui.game_state = game_state
    
    shop_ui = ShopUI(console)
    shop_ui.game_state = game_state
    
    stats_ui = StatsPanel(console)
    stats_ui.game_state = game_state
    
    inventory_ui = InventoryUI(console)
    inventory_ui.game_state = game_state
    
    # Initialize player
    battle_system.initialize_player()
    
    # Introduction
    dialogue_ui.show(
        "Game Master",
        [
            "Welcome to the Goblin Gauntlet!",
            "You are a brave adventurer who has been tasked with clearing out the goblin infestation.",
            "Defeat goblins to earn gold, which you can use to buy items between battles.",
            "Good luck, adventurer!"
        ],
        "The adventure begins..."
    )
    
    # Main game loop
    goblin_difficulty = 1
    player_alive = True
    
    while player_alive:
        # Create a new goblin
        goblin_name = battle_system.create_goblin(goblin_difficulty)
        
        # Battle introduction
        dialogue_ui.show(
            "Game Master",
            [
                f"A {goblin_name} appears!",
                "Prepare for battle!"
            ],
            "Combat begins"
        )
        
        # Battle loop
        goblin_alive = True
        
        while goblin_alive and player_alive:
            # Display battle UI
            battle_system.display_battle_ui()
            
            # Battle options
            battle_choice = choice_ui.show(
                "Battle Actions",
                [
                    Choice(text="Attack", effect=lambda gs: None),  # Effect handled separately
                    choice_with_condition("Use Health Potion", "has_item:Health Potion:1"),
                    Choice(text="View Detailed Stats"),
                    Choice(text="View Inventory")
                ],
                f"Fighting {goblin_name}"
            )
            
            # Handle player's choice
            if battle_choice.text == "Attack":
                # Player attacks
                goblin_defeated = battle_system.player_attack()
                
                if goblin_defeated:
                    goblin_alive = False
                    difficulty = game_state.get_variable("goblin_difficulty")
                    gold_reward = 10 + (difficulty * 5)
                    
                    # Update player stats
                    game_state.increment_stat("goblins_defeated", 1)
                    game_state.increment_stat("gold", gold_reward)
                    
                    dialogue_ui.show(
                        "Game Master",
                        [
                            f"You defeated the {goblin_name}!",
                            f"You found {gold_reward} gold on its body."
                        ],
                        "Victory!"
                    )
                    break
                
                # Goblin attacks back
                time.sleep(0.5)  # Pause for dramatic effect
                player_defeated = battle_system.goblin_attack()
                
                if player_defeated:
                    player_alive = False
                    dialogue_ui.show(
                        "Game Master",
                        [
                            "You have been defeated by the goblin horde!",
                            f"You managed to defeat {game_state.stats['goblins_defeated']} goblins before falling.",
                            "Better luck next time!"
                        ],
                        "Game Over"
                    )
                    break
            
            elif battle_choice.text == "Use Health Potion":
                # Use a health potion
                game_state.remove_from_inventory("Health Potion", 1)
                
                # Calculate healing amount
                heal_amount = 30
                current_health = game_state.stats["health"]
                max_health = game_state.stats["max_health"]
                
                new_health = min(current_health + heal_amount, max_health)
                actual_heal = new_health - current_health
                
                game_state.update_stat("health", new_health)
                
                console.print(f"You drink a Health Potion and restore [bold green]{actual_heal}[/bold green] health!")
                
                # Goblin still attacks
                time.sleep(0.5)
                player_defeated = battle_system.goblin_attack()
                
                if player_defeated:
                    player_alive = False
                    dialogue_ui.show(
                        "Game Master",
                        [
                            "Despite your healing efforts, you have been defeated!",
                            f"You managed to defeat {game_state.stats['goblins_defeated']} goblins before falling.",
                            "Better luck next time!"
                        ],
                        "Game Over"
                    )
                    break
            
            elif battle_choice.text == "View Detailed Stats":
                # Show detailed stats
                stats_ui.show("Adventurer", "Battle Stats")
            
            elif battle_choice.text == "View Inventory":
                # Show inventory
                inventory_ui.show("Adventurer", "Battle Inventory")
        
        # After battle options
        if player_alive:
            # Increase difficulty
            goblin_difficulty += 1
            
            # Visit shop or continue
            after_battle_choice = choice_ui.show(
                "After Battle",
                [
                    Choice(text="Visit Shop"),
                    Choice(text="Rest (Restore 20 Health)", 
                           effect="add_stat:health:20"),
                    Choice(text="Continue to next battle")
                ],
                "What will you do next?"
            )
            
            # Handle after-battle choice
            if after_battle_choice.text == "Visit Shop":
                shop_items = [
                    {"name": "Health Potion", "price": 15, "description": "Restores 30 health"},
                    {"name": "Iron Sword", "price": 50, "description": "Increases attack by 5", 
                     "condition": lambda gs: "Iron Sword" not in gs.inventory},
                    {"name": "Shield", "price": 40, "description": "Increases defense by 3", 
                     "condition": lambda gs: "Shield" not in gs.inventory},
                    {"name": "Speed Boots", "price": 35, "description": "Increases speed by 4", 
                     "condition": lambda gs: "Speed Boots" not in gs.inventory},
                ]
                
                # Show shop UI
                shop_ui.show("Goblin Gauntlet Shop", shop_items, "gold", "Traveling Merchant")
                
                # Apply item effects if purchased
                if "Iron Sword" in game_state.inventory and game_state.inventory["Iron Sword"] > 0:
                    game_state.update_stat("attack", game_state.stats["attack"] + 5)
                    # Remove from inventory to prevent stacking the bonus
                    game_state.inventory["Iron Sword"] = 0
                    
                if "Shield" in game_state.inventory and game_state.inventory["Shield"] > 0:
                    game_state.update_stat("defense", game_state.stats["defense"] + 3)
                    # Remove from inventory to prevent stacking the bonus
                    game_state.inventory["Shield"] = 0
                    
                if "Speed Boots" in game_state.inventory and game_state.inventory["Speed Boots"] > 0:
                    game_state.update_stat("speed", game_state.stats["speed"] + 4)
                    # Remove from inventory to prevent stacking the bonus
                    game_state.inventory["Speed Boots"] = 0
            
            # Display stats before next battle
            dialogue_ui.show(
                "Game Master",
                [
                    f"Prepare for your next challenge!",
                    f"You've defeated {game_state.stats['goblins_defeated']} goblins so far.",
                    "The next goblin will be stronger..."
                ],
                "Onward to battle!"
            )
    
    # End of game
    console.print("\n[bold]Thanks for playing Goblin Gauntlet![/bold]")
    console.print(f"Final score: {game_state.stats['goblins_defeated']} goblins defeated")

if __name__ == "__main__":
    goblin_battle_game()