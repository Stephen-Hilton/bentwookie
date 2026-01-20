"""Game constants and configuration."""

# Map dimensions
MAP_WIDTH = 35
MAP_HEIGHT = 15

# Tile types
WALL = '█'
FLOOR = '.'
PLAYER = '@'
TREASURE = '$'
WEAPON = '†'
MONSTER = 'M'
EXIT = '>'
POTION = '♥'

# Colors for rich
COLORS = {
    WALL: "bright_black",
    FLOOR: "dim white",
    PLAYER: "bright_cyan bold",
    TREASURE: "yellow bold",
    WEAPON: "magenta bold",
    MONSTER: "red bold",
    EXIT: "green bold",
    POTION: "bright_red bold",
}

# Player starting stats
PLAYER_START_HP = 100
PLAYER_START_ATTACK = 5
PLAYER_START_DEFENSE = 2
PLAYER_START_GOLD = 0

# Movement keys
MOVE_KEYS = {
    'w': (0, -1),
    'a': (-1, 0),
    's': (0, 1),
    'd': (1, 0),
    'KEY_UP': (0, -1),
    'KEY_DOWN': (0, 1),
    'KEY_LEFT': (-1, 0),
    'KEY_RIGHT': (1, 0),
}

# Monster definitions: (hp, attack, defense, gold_drop, symbol_color)
MONSTER_TYPES = {
    'Rat': {'hp': 10, 'attack': 3, 'defense': 1, 'gold': 5, 'emoji': '🐀'},
    'Goblin': {'hp': 20, 'attack': 6, 'defense': 2, 'gold': 15, 'emoji': '👺'},
    'Orc': {'hp': 40, 'attack': 10, 'defense': 5, 'gold': 30, 'emoji': '👹'},
    'Troll': {'hp': 60, 'attack': 15, 'defense': 8, 'gold': 50, 'emoji': '🧌'},
    'Dragon': {'hp': 100, 'attack': 25, 'defense': 15, 'gold': 200, 'emoji': '🐉'},
}

# Weapon definitions: (attack_bonus, special_effect, emoji)
WEAPON_TYPES = {
    'Rusty Dagger': {'bonus': 2, 'effect': None, 'emoji': '🗡️'},
    'Short Sword': {'bonus': 5, 'effect': None, 'emoji': '⚔️'},
    'Battle Axe': {'bonus': 8, 'effect': None, 'emoji': '🪓'},
    'Magic Staff': {'bonus': 10, 'effect': 'magic', 'emoji': '🔮'},
    'Flaming Sword': {'bonus': 15, 'effect': 'fire', 'emoji': '🔥'},
    'Frost Blade': {'bonus': 12, 'effect': 'frost', 'emoji': '❄️'},
}

# Treasure values
TREASURE_VALUES = {
    'Gold Coins': {'min': 10, 'max': 50},
    'Silver Coins': {'min': 5, 'max': 20},
    'Ruby': {'value': 100},
    'Emerald': {'value': 75},
    'Diamond': {'value': 150},
}

# Game messages
MESSAGES = {
    'welcome': "Welcome to the Dungeon! Find the exit to advance.",
    'level_up': "Level complete! Descending deeper...",
    'game_over': "You have been defeated! Game Over.",
    'victory': "Congratulations! You escaped the dungeon!",
}

# Number of items per level
ITEMS_PER_LEVEL = {
    'treasures': 5,
    'weapons': 2,
    'monsters': 4,
    'potions': 2,
}

# Potion healing amount
POTION_HEAL = 30

# Max dungeon levels (victory after completing this level)
MAX_LEVELS = 5

# Monster spawn chance increase per level
MONSTER_DIFFICULTY_SCALE = 0.15
