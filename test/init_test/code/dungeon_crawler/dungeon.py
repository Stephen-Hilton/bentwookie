"""Maze generation and dungeon management."""

import random
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass, field
from .constants import (
    MAP_WIDTH, MAP_HEIGHT, WALL, FLOOR, EXIT, TREASURE, WEAPON, MONSTER, POTION,
    ITEMS_PER_LEVEL
)
from .monsters import Monster
from .items import Weapon, Treasure, Potion


@dataclass
class Dungeon:
    """A dungeon level with maze, items, and monsters."""
    width: int = MAP_WIDTH
    height: int = MAP_HEIGHT
    level: int = 1
    tiles: List[List[str]] = field(default_factory=list)
    monsters: Dict[Tuple[int, int], Monster] = field(default_factory=dict)
    items: Dict[Tuple[int, int], Any] = field(default_factory=dict)
    player_start: Tuple[int, int] = (1, 1)
    exit_pos: Tuple[int, int] = (1, 1)

    def __post_init__(self):
        """Generate the dungeon after initialization."""
        if not self.tiles:
            self.generate()

    def generate(self) -> None:
        """Generate a new dungeon maze."""
        # Initialize all walls
        self.tiles = [[WALL for _ in range(self.width)] for _ in range(self.height)]
        self.monsters = {}
        self.items = {}

        # Generate maze using recursive backtracking
        self._generate_maze()

        # Place player start (top-left area)
        self.player_start = self._find_floor_tile(1, 1, self.width // 3, self.height // 2)

        # Place exit (bottom-right area)
        self.exit_pos = self._find_floor_tile(
            self.width * 2 // 3, self.height // 2,
            self.width - 2, self.height - 2
        )
        self.tiles[self.exit_pos[1]][self.exit_pos[0]] = EXIT

        # Place items and monsters
        self._place_items()
        self._place_monsters()

    def _generate_maze(self) -> None:
        """Generate maze using recursive backtracking algorithm."""
        # Start from odd coordinates to ensure walls between paths
        start_x, start_y = 1, 1

        # Stack for backtracking
        stack = [(start_x, start_y)]
        visited = {(start_x, start_y)}
        self.tiles[start_y][start_x] = FLOOR

        while stack:
            x, y = stack[-1]
            neighbors = self._get_unvisited_neighbors(x, y, visited)

            if neighbors:
                # Choose random neighbor
                nx, ny = random.choice(neighbors)
                # Remove wall between current and neighbor
                wall_x, wall_y = (x + nx) // 2, (y + ny) // 2
                self.tiles[wall_y][wall_x] = FLOOR
                self.tiles[ny][nx] = FLOOR
                visited.add((nx, ny))
                stack.append((nx, ny))
            else:
                stack.pop()

        # Add some random openings to make the maze less linear
        self._add_random_openings()

    def _get_unvisited_neighbors(self, x: int, y: int, visited: set) -> List[Tuple[int, int]]:
        """Get unvisited neighbor cells (2 steps away for maze generation)."""
        neighbors = []
        for dx, dy in [(0, -2), (0, 2), (-2, 0), (2, 0)]:
            nx, ny = x + dx, y + dy
            if (1 <= nx < self.width - 1 and 1 <= ny < self.height - 1
                    and (nx, ny) not in visited):
                neighbors.append((nx, ny))
        return neighbors

    def _add_random_openings(self) -> None:
        """Add random openings to make maze more interesting."""
        num_openings = (self.width * self.height) // 50
        for _ in range(num_openings):
            x = random.randint(2, self.width - 3)
            y = random.randint(2, self.height - 3)
            if self.tiles[y][x] == WALL:
                # Check if opening won't create too large an area
                floor_neighbors = sum(
                    1 for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                    if self.tiles[y + dy][x + dx] == FLOOR
                )
                if floor_neighbors >= 2:
                    self.tiles[y][x] = FLOOR

    def _find_floor_tile(self, min_x: int, min_y: int, max_x: int, max_y: int) -> Tuple[int, int]:
        """Find a random floor tile in the given area."""
        floor_tiles = []
        for y in range(max(1, min_y), min(self.height - 1, max_y + 1)):
            for x in range(max(1, min_x), min(self.width - 1, max_x + 1)):
                if self.tiles[y][x] == FLOOR:
                    floor_tiles.append((x, y))

        if floor_tiles:
            return random.choice(floor_tiles)
        # Fallback: find any floor tile
        return self._find_any_floor_tile()

    def _find_any_floor_tile(self) -> Tuple[int, int]:
        """Find any floor tile in the dungeon."""
        for y in range(1, self.height - 1):
            for x in range(1, self.width - 1):
                if self.tiles[y][x] == FLOOR:
                    return (x, y)
        return (1, 1)

    def _get_empty_floor_tiles(self) -> List[Tuple[int, int]]:
        """Get all floor tiles that don't have items/monsters/special tiles."""
        empty_tiles = []
        for y in range(1, self.height - 1):
            for x in range(1, self.width - 1):
                if (self.tiles[y][x] == FLOOR
                        and (x, y) != self.player_start
                        and (x, y) != self.exit_pos
                        and (x, y) not in self.items
                        and (x, y) not in self.monsters):
                    empty_tiles.append((x, y))
        return empty_tiles

    def _place_items(self) -> None:
        """Place treasures, weapons, and potions."""
        empty_tiles = self._get_empty_floor_tiles()
        random.shuffle(empty_tiles)

        # Scale items with level
        num_treasures = ITEMS_PER_LEVEL['treasures'] + self.level
        num_weapons = ITEMS_PER_LEVEL['weapons']
        num_potions = ITEMS_PER_LEVEL['potions'] + (self.level // 2)

        items_to_place = []

        # Create treasures
        for _ in range(num_treasures):
            items_to_place.append(('treasure', Treasure.random()))

        # Create weapons (better weapons at higher levels)
        for _ in range(num_weapons):
            min_tier = max(0, self.level - 2)
            items_to_place.append(('weapon', Weapon.random(min_tier)))

        # Create potions
        for _ in range(num_potions):
            items_to_place.append(('potion', Potion()))

        # Place items
        for i, (item_type, item) in enumerate(items_to_place):
            if i < len(empty_tiles):
                pos = empty_tiles[i]
                self.items[pos] = item
                # Update tile display
                if item_type == 'treasure':
                    self.tiles[pos[1]][pos[0]] = TREASURE
                elif item_type == 'weapon':
                    self.tiles[pos[1]][pos[0]] = WEAPON
                elif item_type == 'potion':
                    self.tiles[pos[1]][pos[0]] = POTION

    def _place_monsters(self) -> None:
        """Place monsters throughout the dungeon."""
        empty_tiles = self._get_empty_floor_tiles()
        random.shuffle(empty_tiles)

        # More monsters at higher levels
        num_monsters = ITEMS_PER_LEVEL['monsters'] + self.level

        for i in range(min(num_monsters, len(empty_tiles))):
            pos = empty_tiles[i]
            monster = Monster.random(self.level, pos[0], pos[1])
            self.monsters[pos] = monster
            self.tiles[pos[1]][pos[0]] = MONSTER

    def get_tile(self, x: int, y: int) -> str:
        """Get the tile at the given position."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x]
        return WALL

    def is_walkable(self, x: int, y: int) -> bool:
        """Check if the tile at position is walkable."""
        tile = self.get_tile(x, y)
        return tile != WALL

    def get_monster_at(self, x: int, y: int) -> Optional[Monster]:
        """Get monster at position, if any."""
        return self.monsters.get((x, y))

    def get_item_at(self, x: int, y: int) -> Optional[Any]:
        """Get item at position, if any."""
        return self.items.get((x, y))

    def remove_monster(self, x: int, y: int) -> None:
        """Remove a monster from the dungeon."""
        if (x, y) in self.monsters:
            del self.monsters[(x, y)]
            self.tiles[y][x] = FLOOR

    def remove_item(self, x: int, y: int) -> None:
        """Remove an item from the dungeon."""
        if (x, y) in self.items:
            del self.items[(x, y)]
            self.tiles[y][x] = FLOOR

    def is_exit(self, x: int, y: int) -> bool:
        """Check if position is the exit."""
        return (x, y) == self.exit_pos
