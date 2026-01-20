"""Player class with stats, inventory, and movement."""

from dataclasses import dataclass, field
from typing import Tuple
from .constants import (
    PLAYER_START_HP, PLAYER_START_ATTACK, PLAYER_START_DEFENSE,
    PLAYER_START_GOLD, MOVE_KEYS
)
from .items import Inventory, Weapon, Potion, Treasure


@dataclass
class Player:
    """The player character."""
    x: int = 1
    y: int = 1
    hp: int = PLAYER_START_HP
    max_hp: int = PLAYER_START_HP
    base_attack: int = PLAYER_START_ATTACK
    defense: int = PLAYER_START_DEFENSE
    gold: int = PLAYER_START_GOLD
    level: int = 1
    inventory: Inventory = field(default_factory=Inventory)

    @property
    def attack(self) -> int:
        """Total attack including weapon bonus."""
        return self.base_attack + self.inventory.get_weapon_bonus()

    @property
    def weapon_effect(self) -> str | None:
        """Special effect of equipped weapon."""
        return self.inventory.get_weapon_effect()

    @property
    def equipped_weapon(self) -> Weapon | None:
        """Currently equipped weapon."""
        return self.inventory.equipped_weapon

    @property
    def is_alive(self) -> bool:
        """Check if player is still alive."""
        return self.hp > 0

    @property
    def hp_percentage(self) -> float:
        """HP as a percentage of max HP."""
        return self.hp / self.max_hp

    @property
    def position(self) -> Tuple[int, int]:
        """Current position as (x, y) tuple."""
        return (self.x, self.y)

    def move(self, dx: int, dy: int) -> None:
        """Move the player by the given delta."""
        self.x += dx
        self.y += dy

    def move_to(self, x: int, y: int) -> None:
        """Move the player to a specific position."""
        self.x = x
        self.y = y

    def get_move_delta(self, key: str) -> Tuple[int, int] | None:
        """Get movement delta for a key press."""
        return MOVE_KEYS.get(key.lower() if len(key) == 1 else key)

    def take_damage(self, damage: int) -> int:
        """Take damage and return actual damage taken."""
        actual_damage = max(1, damage - self.defense)
        self.hp = max(0, self.hp - actual_damage)
        return actual_damage

    def heal(self, amount: int) -> int:
        """Heal the player and return actual amount healed."""
        old_hp = self.hp
        self.hp = min(self.max_hp, self.hp + amount)
        return self.hp - old_hp

    def use_potion(self) -> Tuple[bool, int]:
        """Use a health potion. Returns (success, amount_healed)."""
        heal_amount = self.inventory.use_potion()
        if heal_amount is not None:
            actual_heal = self.heal(heal_amount)
            return True, actual_heal
        return False, 0

    def collect_treasure(self, treasure: Treasure) -> None:
        """Collect a treasure item."""
        self.gold += treasure.value

    def collect_weapon(self, weapon: Weapon) -> bool:
        """Collect a weapon. Returns True if auto-equipped."""
        return self.inventory.add_weapon(weapon)

    def collect_potion(self, potion: Potion) -> None:
        """Collect a health potion."""
        self.inventory.add_potion(potion)

    def level_up(self) -> None:
        """Level up the player, improving stats."""
        self.level += 1
        # Increase stats
        self.max_hp += 10
        self.hp = min(self.hp + 20, self.max_hp)  # Partial heal on level up
        self.base_attack += 2
        self.defense += 1

    def reset_position(self, x: int, y: int) -> None:
        """Reset player position for a new level."""
        self.x = x
        self.y = y
