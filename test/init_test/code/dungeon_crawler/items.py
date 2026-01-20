"""Weapon and treasure item classes."""

from dataclasses import dataclass
from typing import Optional
import random
from .constants import WEAPON_TYPES, TREASURE_VALUES, POTION_HEAL


@dataclass
class Weapon:
    """A weapon that can be equipped by the player."""
    name: str
    attack_bonus: int
    effect: Optional[str]
    emoji: str

    @classmethod
    def create(cls, name: str) -> 'Weapon':
        """Create a weapon from the predefined types."""
        if name not in WEAPON_TYPES:
            raise ValueError(f"Unknown weapon type: {name}")
        data = WEAPON_TYPES[name]
        return cls(
            name=name,
            attack_bonus=data['bonus'],
            effect=data['effect'],
            emoji=data['emoji']
        )

    @classmethod
    def random(cls, min_tier: int = 0) -> 'Weapon':
        """Create a random weapon, with optional minimum tier."""
        weapons = list(WEAPON_TYPES.keys())
        # Higher tiers are later in the list
        available = weapons[min_tier:] if min_tier < len(weapons) else weapons[-2:]
        name = random.choice(available)
        return cls.create(name)

    def __str__(self) -> str:
        effect_str = f" [{self.effect}]" if self.effect else ""
        return f"{self.emoji} {self.name} (+{self.attack_bonus}){effect_str}"


@dataclass
class Treasure:
    """A treasure item that gives gold or other bonuses."""
    name: str
    value: int
    emoji: str = "💰"

    @classmethod
    def random(cls) -> 'Treasure':
        """Create a random treasure."""
        # 70% chance for coins, 30% for gems
        if random.random() < 0.7:
            # Coins
            coin_type = random.choice(['Gold Coins', 'Silver Coins'])
            data = TREASURE_VALUES[coin_type]
            value = random.randint(data['min'], data['max'])
            emoji = "🪙" if coin_type == 'Gold Coins' else "🥈"
            return cls(name=coin_type, value=value, emoji=emoji)
        else:
            # Gems
            gem_type = random.choice(['Ruby', 'Emerald', 'Diamond'])
            data = TREASURE_VALUES[gem_type]
            value = data['value']
            emoji = {'Ruby': '💎', 'Emerald': '💚', 'Diamond': '💠'}[gem_type]
            return cls(name=gem_type, value=value, emoji=emoji)

    def __str__(self) -> str:
        return f"{self.emoji} {self.name} ({self.value} gold)"


@dataclass
class Potion:
    """A health potion that restores HP."""
    heal_amount: int = POTION_HEAL
    emoji: str = "🧪"

    def __str__(self) -> str:
        return f"{self.emoji} Health Potion (+{self.heal_amount} HP)"


class Inventory:
    """Player inventory for storing items."""

    def __init__(self):
        self.weapons: list[Weapon] = []
        self.potions: list[Potion] = []
        self.equipped_weapon: Optional[Weapon] = None

    def add_weapon(self, weapon: Weapon) -> bool:
        """Add a weapon to inventory. Returns True if it was auto-equipped."""
        self.weapons.append(weapon)
        # Auto-equip if it's better than current
        if self.equipped_weapon is None or weapon.attack_bonus > self.equipped_weapon.attack_bonus:
            self.equipped_weapon = weapon
            return True
        return False

    def add_potion(self, potion: Potion) -> None:
        """Add a potion to inventory."""
        self.potions.append(potion)

    def use_potion(self) -> Optional[int]:
        """Use a potion and return heal amount, or None if no potions."""
        if self.potions:
            potion = self.potions.pop()
            return potion.heal_amount
        return None

    def get_weapon_bonus(self) -> int:
        """Get the attack bonus from equipped weapon."""
        return self.equipped_weapon.attack_bonus if self.equipped_weapon else 0

    def get_weapon_effect(self) -> Optional[str]:
        """Get the special effect of equipped weapon."""
        return self.equipped_weapon.effect if self.equipped_weapon else None

    @property
    def potion_count(self) -> int:
        """Number of potions in inventory."""
        return len(self.potions)
