"""Turn-based combat system."""

import random
from dataclasses import dataclass
from typing import List, Tuple
from .player import Player
from .monsters import Monster


@dataclass
class CombatResult:
    """Result of a combat action."""
    attacker: str
    defender: str
    damage: int
    is_critical: bool = False
    special_effect: str | None = None
    defender_hp: int = 0
    defender_max_hp: int = 0

    @property
    def message(self) -> str:
        """Generate combat message."""
        crit_str = " CRITICAL HIT!" if self.is_critical else ""
        effect_str = f" ({self.special_effect})" if self.special_effect else ""
        return f"{self.attacker} deals {self.damage} damage to {self.defender}!{crit_str}{effect_str}"


class Combat:
    """Manages combat between player and monster."""

    CRITICAL_CHANCE = 0.15
    FLEE_BASE_CHANCE = 0.4

    def __init__(self, player: Player, monster: Monster):
        self.player = player
        self.monster = monster
        self.combat_log: List[CombatResult] = []
        self.is_active = True
        self.player_fled = False

    def player_attack(self) -> CombatResult:
        """Player attacks the monster."""
        damage = self._calculate_damage(
            self.player.attack,
            self.monster.defense,
            self.player.weapon_effect
        )

        is_critical = random.random() < self.CRITICAL_CHANCE
        if is_critical:
            damage = int(damage * 1.5)

        # Apply special weapon effects
        special_effect = None
        if self.player.weapon_effect:
            special_effect = self._apply_weapon_effect(self.player.weapon_effect, damage)

        actual_damage = self.monster.take_damage(damage)

        result = CombatResult(
            attacker="You",
            defender=self.monster.name,
            damage=actual_damage,
            is_critical=is_critical,
            special_effect=special_effect,
            defender_hp=self.monster.hp,
            defender_max_hp=self.monster.max_hp
        )
        self.combat_log.append(result)

        if not self.monster.is_alive:
            self.is_active = False

        return result

    def monster_attack(self) -> CombatResult | None:
        """Monster attacks the player."""
        if not self.monster.is_alive:
            return None

        damage = self._calculate_damage(
            self.monster.attack,
            self.player.defense,
            None
        )

        is_critical = random.random() < self.CRITICAL_CHANCE
        if is_critical:
            damage = int(damage * 1.5)

        actual_damage = self.player.take_damage(damage)

        result = CombatResult(
            attacker=self.monster.name,
            defender="You",
            damage=actual_damage,
            is_critical=is_critical,
            defender_hp=self.player.hp,
            defender_max_hp=self.player.max_hp
        )
        self.combat_log.append(result)

        if not self.player.is_alive:
            self.is_active = False

        return result

    def attempt_flee(self) -> Tuple[bool, str]:
        """Attempt to flee from combat."""
        # Flee chance based on player level vs monster tier
        flee_chance = self.FLEE_BASE_CHANCE + (self.player.level * 0.1)
        flee_chance = min(0.9, flee_chance)  # Cap at 90%

        if random.random() < flee_chance:
            self.is_active = False
            self.player_fled = True
            return True, "You successfully fled from combat!"
        else:
            return False, f"Failed to flee! {self.monster.name} blocks your escape!"

    def use_potion(self) -> Tuple[bool, str]:
        """Use a health potion during combat."""
        success, amount = self.player.use_potion()
        if success:
            return True, f"You drink a potion and restore {amount} HP!"
        else:
            return False, "You don't have any potions!"

    def _calculate_damage(self, attack: int, defense: int, effect: str | None) -> int:
        """Calculate damage with some randomness."""
        base_damage = max(1, attack - defense)
        # Add variance (-20% to +20%)
        variance = random.uniform(0.8, 1.2)
        damage = int(base_damage * variance)

        # Weapon effects add bonus damage
        if effect == 'fire':
            damage += random.randint(2, 6)
        elif effect == 'frost':
            damage += random.randint(1, 4)
        elif effect == 'magic':
            damage += random.randint(3, 5)

        return max(1, damage)

    def _apply_weapon_effect(self, effect: str, damage: int) -> str | None:
        """Apply special weapon effect and return description."""
        if effect == 'fire':
            return "🔥 Burns!"
        elif effect == 'frost':
            return "❄️ Freezing!"
        elif effect == 'magic':
            return "🔮 Arcane blast!"
        return None

    @property
    def player_won(self) -> bool:
        """Check if player won the combat."""
        return not self.is_active and not self.monster.is_alive and self.player.is_alive

    @property
    def player_lost(self) -> bool:
        """Check if player lost the combat."""
        return not self.is_active and not self.player.is_alive

    def get_loot(self) -> Tuple[int, str]:
        """Get loot from defeated monster."""
        if not self.player_won:
            return 0, ""
        gold = self.monster.gold_drop
        self.player.gold += gold
        return gold, f"You defeated {self.monster.name} and found {gold} gold!"
