"""Core game state management."""

from enum import Enum, auto
from typing import Optional, Tuple
from .player import Player
from .dungeon import Dungeon
from .combat import Combat
from .renderer import Renderer
from .items import Weapon, Treasure, Potion
from .constants import MAX_LEVELS


class GameState(Enum):
    """Current state of the game."""
    TITLE = auto()
    PLAYING = auto()
    COMBAT = auto()
    LEVEL_COMPLETE = auto()
    GAME_OVER = auto()
    VICTORY = auto()


class Game:
    """Main game class managing state and logic."""

    def __init__(self):
        self.player = Player()
        self.dungeon = Dungeon(level=1)
        self.renderer = Renderer()
        self.state = GameState.TITLE
        self.combat: Optional[Combat] = None
        self.running = True

        # Set player starting position
        self.player.move_to(*self.dungeon.player_start)

    def handle_input(self, key: str) -> None:
        """Handle player input based on current game state."""
        if self.state == GameState.TITLE:
            self.state = GameState.PLAYING
            self.renderer.add_message("Welcome to the dungeon! Find the exit >")

        elif self.state == GameState.PLAYING:
            self._handle_movement(key)

        elif self.state == GameState.COMBAT:
            self._handle_combat(key)

        elif self.state == GameState.LEVEL_COMPLETE:
            self._advance_level()

        elif self.state in (GameState.GAME_OVER, GameState.VICTORY):
            self.running = False

    def _handle_movement(self, key: str) -> None:
        """Handle movement and exploration."""
        key_lower = key.lower() if len(key) == 1 else key

        if key_lower == 'q':
            self.running = False
            return

        if key_lower == 'p':
            success, amount = self.player.use_potion()
            if success:
                self.renderer.add_message(f"🧪 Used potion! Restored {amount} HP")
            else:
                self.renderer.add_message("No potions available!")
            return

        # Try to move
        delta = self.player.get_move_delta(key)
        if delta:
            new_x = self.player.x + delta[0]
            new_y = self.player.y + delta[1]

            if self.dungeon.is_walkable(new_x, new_y):
                # Check what's at the new position
                self._process_tile(new_x, new_y)

    def _process_tile(self, x: int, y: int) -> None:
        """Process the tile the player is moving to."""
        # Check for monster
        monster = self.dungeon.get_monster_at(x, y)
        if monster:
            self._start_combat(monster)
            return

        # Move player
        self.player.move_to(x, y)

        # Check for items
        item = self.dungeon.get_item_at(x, y)
        if item:
            self._collect_item(x, y, item)

        # Check for exit
        if self.dungeon.is_exit(x, y):
            self._reach_exit()

    def _collect_item(self, x: int, y: int, item) -> None:
        """Collect an item at the given position."""
        if isinstance(item, Treasure):
            self.player.collect_treasure(item)
            self.renderer.add_message(f"💰 Found {item}!")
        elif isinstance(item, Weapon):
            auto_equipped = self.player.collect_weapon(item)
            if auto_equipped:
                self.renderer.add_message(f"⚔️ Found {item}! Equipped automatically!")
            else:
                self.renderer.add_message(f"⚔️ Found {item}!")
        elif isinstance(item, Potion):
            self.player.collect_potion(item)
            self.renderer.add_message(f"🧪 Found a Health Potion!")

        self.dungeon.remove_item(x, y)

    def _start_combat(self, monster) -> None:
        """Start combat with a monster."""
        self.combat = Combat(self.player, monster)
        self.state = GameState.COMBAT
        self.renderer.add_message(f"⚔️ A {monster.name} appears!")

    def _handle_combat(self, key: str) -> None:
        """Handle combat input."""
        if not self.combat or not self.combat.is_active:
            return

        key_lower = key.lower() if len(key) == 1 else key

        if key_lower == 'a':
            # Player attack
            result = self.combat.player_attack()
            self.renderer.add_message(result.message)

            if self.combat.player_won:
                self._end_combat(victory=True)
                return

            # Monster counter-attack
            result = self.combat.monster_attack()
            if result:
                self.renderer.add_message(result.message)

            if self.combat.player_lost:
                self._end_combat(victory=False)

        elif key_lower == 'p':
            # Use potion
            success, msg = self.combat.use_potion()
            self.renderer.add_message(msg)

            if success:
                # Monster still attacks
                result = self.combat.monster_attack()
                if result:
                    self.renderer.add_message(result.message)

                if self.combat.player_lost:
                    self._end_combat(victory=False)

        elif key_lower == 'f':
            # Try to flee
            success, msg = self.combat.attempt_flee()
            self.renderer.add_message(msg)

            if success:
                self.state = GameState.PLAYING
                self.combat = None
            else:
                # Monster attacks on failed flee
                result = self.combat.monster_attack()
                if result:
                    self.renderer.add_message(result.message)

                if self.combat.player_lost:
                    self._end_combat(victory=False)

    def _end_combat(self, victory: bool) -> None:
        """End the current combat."""
        if victory:
            # Collect loot
            gold, msg = self.combat.get_loot()
            self.renderer.add_message(msg)

            # Remove monster from dungeon
            monster = self.combat.monster
            self.dungeon.remove_monster(monster.x, monster.y)

            # Move player to monster's position
            self.player.move_to(monster.x, monster.y)

            self.state = GameState.PLAYING
        else:
            self.state = GameState.GAME_OVER

        self.combat = None

    def _reach_exit(self) -> None:
        """Player reached the level exit."""
        if self.dungeon.level >= MAX_LEVELS:
            self.state = GameState.VICTORY
        else:
            self.state = GameState.LEVEL_COMPLETE

    def _advance_level(self) -> None:
        """Advance to the next dungeon level."""
        new_level = self.dungeon.level + 1
        self.player.level_up()
        self.dungeon = Dungeon(level=new_level)
        self.player.move_to(*self.dungeon.player_start)
        self.state = GameState.PLAYING
        self.renderer.add_message(f"⬇️ Descended to level {new_level}!")

    def render(self) -> None:
        """Render the current game state."""
        if self.state == GameState.TITLE:
            self.renderer.render_title_screen()
        elif self.state in (GameState.PLAYING, GameState.COMBAT):
            self.renderer.render_game(self.dungeon, self.player, self.combat)
        elif self.state == GameState.LEVEL_COMPLETE:
            self.renderer.render_level_complete(self.dungeon.level)
        elif self.state == GameState.GAME_OVER:
            self.renderer.render_game_over(self.player, victory=False)
        elif self.state == GameState.VICTORY:
            self.renderer.render_game_over(self.player, victory=True)
