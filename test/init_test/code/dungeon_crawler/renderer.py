"""Rich-based terminal rendering."""

from typing import List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.text import Text
from rich.progress import Progress, BarColumn, TextColumn
from rich import box

from .constants import COLORS, WALL, FLOOR, PLAYER, EXIT, TREASURE, WEAPON, MONSTER, POTION
from .player import Player
from .dungeon import Dungeon
from .monsters import Monster
from .combat import Combat


class Renderer:
    """Handles all terminal rendering using Rich."""

    def __init__(self):
        self.console = Console()
        self.message_log: List[str] = []
        self.max_messages = 5

    def clear(self) -> None:
        """Clear the terminal."""
        self.console.clear()

    def add_message(self, message: str) -> None:
        """Add a message to the log."""
        self.message_log.append(message)
        if len(self.message_log) > self.max_messages:
            self.message_log.pop(0)

    def render_game(self, dungeon: Dungeon, player: Player, combat: Optional[Combat] = None) -> None:
        """Render the full game screen."""
        self.clear()

        # Create layout
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=8)
        )

        # Header
        header_text = Text()
        header_text.append("⚔️  DUNGEON CRAWLER  ⚔️", style="bold bright_cyan")
        header_text.append(f"   Level {dungeon.level}", style="yellow")
        layout["header"].update(Panel(header_text, box=box.DOUBLE))

        # Main area split
        layout["main"].split_row(
            Layout(name="map", ratio=2),
            Layout(name="status", ratio=1)
        )

        # Map
        map_display = self._render_map(dungeon, player)
        layout["map"].update(Panel(map_display, title="[bold]Dungeon Map[/bold]", border_style="blue"))

        # Status
        if combat and combat.is_active:
            status_display = self._render_combat_status(player, combat)
        else:
            status_display = self._render_status(player)
        layout["status"].update(Panel(status_display, title="[bold]Status[/bold]", border_style="green"))

        # Footer - controls and messages
        layout["footer"].split_row(
            Layout(name="log", ratio=2),
            Layout(name="controls", ratio=1)
        )

        # Message log
        log_text = Text()
        for msg in self.message_log[-5:]:
            log_text.append(msg + "\n", style="dim white")
        layout["log"].update(Panel(log_text, title="[bold]Combat Log[/bold]", border_style="yellow"))

        # Controls
        if combat and combat.is_active:
            controls = self._render_combat_controls()
        else:
            controls = self._render_controls()
        layout["controls"].update(Panel(controls, title="[bold]Controls[/bold]", border_style="magenta"))

        self.console.print(layout)

    def _render_map(self, dungeon: Dungeon, player: Player) -> Text:
        """Render the dungeon map with colors."""
        text = Text()

        for y in range(dungeon.height):
            for x in range(dungeon.width):
                # Check if player is at this position
                if (x, y) == player.position:
                    text.append(PLAYER, style=COLORS[PLAYER])
                else:
                    tile = dungeon.get_tile(x, y)
                    style = COLORS.get(tile, "white")
                    text.append(tile, style=style)
            text.append("\n")

        # Legend
        text.append("\n")
        text.append(f"  {PLAYER}", style=COLORS[PLAYER])
        text.append(" You  ")
        text.append(f"{MONSTER}", style=COLORS[MONSTER])
        text.append(" Monster  ")
        text.append(f"{TREASURE}", style=COLORS[TREASURE])
        text.append(" Treasure  ")
        text.append(f"{WEAPON}", style=COLORS[WEAPON])
        text.append(" Weapon  ")
        text.append(f"{EXIT}", style=COLORS[EXIT])
        text.append(" Exit")

        return text

    def _render_status(self, player: Player) -> Text:
        """Render player status panel."""
        text = Text()

        # HP bar
        text.append("HP: ", style="bold")
        hp_pct = player.hp_percentage
        hp_filled = int(hp_pct * 10)
        hp_empty = 10 - hp_filled
        hp_color = "green" if hp_pct > 0.5 else "yellow" if hp_pct > 0.25 else "red"
        text.append("█" * hp_filled, style=hp_color)
        text.append("░" * hp_empty, style="dim")
        text.append(f" {player.hp}/{player.max_hp}\n", style="bold")

        # Stats
        text.append(f"\nATK: ", style="bold red")
        text.append(f"{player.attack}")
        text.append(f"  DEF: ", style="bold blue")
        text.append(f"{player.defense}\n")

        text.append(f"\n💰 Gold: ", style="bold yellow")
        text.append(f"{player.gold}\n")

        # Weapon
        text.append(f"\n⚔️  WEAPON\n", style="bold magenta")
        if player.equipped_weapon:
            text.append(f"   {player.equipped_weapon}\n")
        else:
            text.append("   None equipped\n", style="dim")

        # Inventory
        text.append(f"\n📦 INVENTORY\n", style="bold cyan")
        if player.inventory.potion_count > 0:
            text.append(f"   🧪 Health Potion x{player.inventory.potion_count}\n")
        if len(player.inventory.weapons) > 1:
            for w in player.inventory.weapons:
                if w != player.equipped_weapon:
                    text.append(f"   {w}\n", style="dim")

        return text

    def _render_combat_status(self, player: Player, combat: Combat) -> Text:
        """Render combat status panel."""
        text = Text()
        monster = combat.monster

        # Monster info
        text.append(f"⚔️  COMBAT!\n\n", style="bold red")
        text.append(f"{monster.emoji} {monster.name}\n", style="bold")

        # Monster HP bar
        text.append("HP: ", style="bold")
        hp_pct = monster.hp_percentage
        hp_filled = int(hp_pct * 10)
        hp_empty = 10 - hp_filled
        hp_color = "green" if hp_pct > 0.5 else "yellow" if hp_pct > 0.25 else "red"
        text.append("█" * hp_filled, style=hp_color)
        text.append("░" * hp_empty, style="dim")
        text.append(f" {monster.hp}/{monster.max_hp}\n")

        text.append(f"ATK: {monster.attack}  DEF: {monster.defense}\n\n")

        text.append("─" * 20 + "\n\n")

        # Player HP
        text.append("YOUR HP: ", style="bold")
        hp_pct = player.hp_percentage
        hp_filled = int(hp_pct * 10)
        hp_empty = 10 - hp_filled
        hp_color = "green" if hp_pct > 0.5 else "yellow" if hp_pct > 0.25 else "red"
        text.append("█" * hp_filled, style=hp_color)
        text.append("░" * hp_empty, style="dim")
        text.append(f" {player.hp}/{player.max_hp}\n")

        text.append(f"\n🧪 Potions: {player.inventory.potion_count}\n")

        return text

    def _render_controls(self) -> Text:
        """Render movement controls."""
        text = Text()
        text.append("[W/↑] Up\n", style="bold")
        text.append("[S/↓] Down\n", style="bold")
        text.append("[A/←] Left\n", style="bold")
        text.append("[D/→] Right\n", style="bold")
        text.append("\n[P] Potion\n", style="cyan")
        text.append("[Q] Quit\n", style="red")
        return text

    def _render_combat_controls(self) -> Text:
        """Render combat controls."""
        text = Text()
        text.append("[A] Attack\n", style="bold red")
        text.append("[P] Potion\n", style="bold cyan")
        text.append("[F] Flee\n", style="bold yellow")
        return text

    def render_title_screen(self) -> None:
        """Render the title screen."""
        self.clear()

        title = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║     ██████╗ ██╗   ██╗███╗   ██╗ ██████╗ ███████╗ ██████╗ ███╗   ██╗ ║
║     ██╔══██╗██║   ██║████╗  ██║██╔════╝ ██╔════╝██╔═══██╗████╗  ██║ ║
║     ██║  ██║██║   ██║██╔██╗ ██║██║  ███╗█████╗  ██║   ██║██╔██╗ ██║ ║
║     ██║  ██║██║   ██║██║╚██╗██║██║   ██║██╔══╝  ██║   ██║██║╚██╗██║ ║
║     ██████╔╝╚██████╔╝██║ ╚████║╚██████╔╝███████╗╚██████╔╝██║ ╚████║ ║
║     ╚═════╝  ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝ ╚══════╝ ╚═════╝ ╚═╝  ╚═══╝ ║
║                                                               ║
║      ██████╗██████╗  █████╗ ██╗    ██╗██╗     ███████╗██████╗  ║
║     ██╔════╝██╔══██╗██╔══██╗██║    ██║██║     ██╔════╝██╔══██╗ ║
║     ██║     ██████╔╝███████║██║ █╗ ██║██║     █████╗  ██████╔╝ ║
║     ██║     ██╔══██╗██╔══██║██║███╗██║██║     ██╔══╝  ██╔══██╗ ║
║     ╚██████╗██║  ██║██║  ██║╚███╔███╔╝███████╗███████╗██║  ██║ ║
║      ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚══╝╚══╝ ╚══════╝╚══════╝╚═╝  ╚═╝ ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
"""
        self.console.print(Text(title, style="bold bright_cyan"))
        self.console.print("\n")
        self.console.print(Panel(
            "[bold yellow]Navigate the dungeon, defeat monsters, collect treasure![/bold yellow]\n\n"
            "[cyan]• Fight 5 types of monsters from Rats to Dragons[/cyan]\n"
            "[magenta]• Find magic weapons with special effects[/magenta]\n"
            "[yellow]• Collect gold and treasures[/yellow]\n"
            "[green]• Descend through 5 dungeon levels to escape![/green]\n\n"
            "[bold white]Press any key to start...[/bold white]",
            title="⚔️  Welcome, Adventurer!  ⚔️",
            border_style="bright_cyan"
        ))

    def render_game_over(self, player: Player, victory: bool) -> None:
        """Render game over screen."""
        self.clear()

        if victory:
            title = Text("🏆 VICTORY! 🏆", style="bold bright_green")
            message = "You escaped the dungeon!"
            color = "green"
        else:
            title = Text("💀 GAME OVER 💀", style="bold bright_red")
            message = "You have been defeated..."
            color = "red"

        stats = Table(show_header=False, box=box.ROUNDED)
        stats.add_column("Stat", style="bold")
        stats.add_column("Value", style="yellow")
        stats.add_row("Final Level", str(player.level))
        stats.add_row("Gold Collected", str(player.gold))
        stats.add_row("Weapons Found", str(len(player.inventory.weapons)))

        self.console.print("\n" * 3)
        self.console.print(Panel(
            title,
            border_style=color,
            padding=(1, 10)
        ), justify="center")

        self.console.print(f"\n[bold {color}]{message}[/bold {color}]", justify="center")
        self.console.print("\n")
        self.console.print(Panel(stats, title="Final Stats", border_style="yellow"), justify="center")
        self.console.print("\n[dim]Press any key to exit...[/dim]", justify="center")

    def render_level_complete(self, level: int) -> None:
        """Render level complete message."""
        self.clear()
        self.console.print("\n" * 5)
        self.console.print(Panel(
            f"[bold green]Level {level} Complete![/bold green]\n\n"
            f"[yellow]Descending to level {level + 1}...[/yellow]",
            title="⬇️  Going Deeper  ⬇️",
            border_style="green"
        ), justify="center")
