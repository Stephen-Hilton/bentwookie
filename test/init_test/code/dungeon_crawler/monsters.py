"""Monster classes with stats and AI behavior."""

from dataclasses import dataclass
from typing import Tuple
import random
from .constants import MONSTER_TYPES, MONSTER_DIFFICULTY_SCALE


@dataclass
class Monster:
    """A monster enemy in the dungeon."""
    name: str
    hp: int
    max_hp: int
    attack: int
    defense: int
    gold_drop: int
    emoji: str
    x: int = 0
    y: int = 0

    @classmethod
    def create(cls, name: str, x: int = 0, y: int = 0, level_bonus: int = 0) -> 'Monster':
        """Create a monster from predefined types with optional level scaling."""
        if name not in MONSTER_TYPES:
            raise ValueError(f"Unknown monster type: {name}")
        data = MONSTER_TYPES[name]

        # Apply level scaling
        scale = 1 + (level_bonus * MONSTER_DIFFICULTY_SCALE)
        hp = int(data['hp'] * scale)
        attack = int(data['attack'] * scale)
        defense = int(data['defense'] * scale)
        gold = int(data['gold'] * scale)

        return cls(
            name=name,
            hp=hp,
            max_hp=hp,
            attack=attack,
            defense=defense,
            gold_drop=gold,
            emoji=data['emoji'],
            x=x,
            y=y
        )

    @classmethod
    def random(cls, level: int = 1, x: int = 0, y: int = 0) -> 'Monster':
        """Create a random monster appropriate for the dungeon level."""
        monsters = list(MONSTER_TYPES.keys())

        # Weight monster selection by level
        # Lower levels have weaker monsters, higher levels introduce stronger ones
        max_index = min(level, len(monsters))
        weights = []
        for i in range(len(monsters)):
            if i < max_index:
                # Available monsters get decreasing weights (common at low tier)
                weights.append(max_index - i)
            else:
                # Higher tier monsters have small chance to appear
                weights.append(max(1, level - i))

        name = random.choices(monsters, weights=weights)[0]
        return cls.create(name, x, y, level_bonus=level - 1)

    @property
    def is_alive(self) -> bool:
        """Check if monster is still alive."""
        return self.hp > 0

    @property
    def hp_percentage(self) -> float:
        """HP as a percentage of max HP."""
        return self.hp / self.max_hp

    @property
    def position(self) -> Tuple[int, int]:
        """Current position as (x, y) tuple."""
        return (self.x, self.y)

    def take_damage(self, damage: int) -> int:
        """Take damage and return actual damage taken."""
        actual_damage = max(1, damage - self.defense)
        self.hp = max(0, self.hp - actual_damage)
        return actual_damage

    def move_to(self, x: int, y: int) -> None:
        """Move monster to a specific position."""
        self.x = x
        self.y = y

    def __str__(self) -> str:
        return f"{self.emoji} {self.name} (HP: {self.hp}/{self.max_hp})"

    @property
    def description(self) -> str:
        """Detailed description for combat."""
        return (
            f"{self.emoji} {self.name}\n"
            f"  HP: {self.hp}/{self.max_hp}\n"
            f"  ATK: {self.attack} | DEF: {self.defense}"
        )


def get_monster_tier(name: str) -> int:
    """Get the tier/difficulty level of a monster type."""
    monsters = list(MONSTER_TYPES.keys())
    return monsters.index(name) if name in monsters else 0
