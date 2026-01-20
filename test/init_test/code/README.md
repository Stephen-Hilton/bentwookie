# Dungeon Crawler

A terminal-based dungeon crawler game featuring procedurally generated mazes, turn-based combat, treasure collection, and magic weapons.

## Features

- **Procedurally Generated Dungeons**: Each playthrough features unique maze layouts
- **5 Monster Types**: From Rats to Dragons, with scaling difficulty
- **6 Magic Weapons**: Including Flaming Sword, Frost Blade, and Magic Staff
- **Turn-Based Combat**: Strategic fights with attack, potion, and flee options
- **Treasure Collection**: Gold, gems, and health potions
- **5 Dungeon Levels**: Descend deeper to escape!
- **Colorful Terminal UI**: Rich ASCII graphics with the `rich` library

## Installation

```bash
cd code
pip install -r requirements.txt
```

## How to Play

```bash
python -m dungeon_crawler.main
```

## Controls

### Exploration
- **W/↑** - Move up
- **S/↓** - Move down
- **A/←** - Move left
- **D/→** - Move right
- **P** - Use health potion
- **Q** - Quit game

### Combat
- **A** - Attack
- **P** - Use health potion
- **F** - Flee

## Game Symbols

| Symbol | Meaning |
|--------|---------|
| `@` | Player |
| `█` | Wall |
| `.` | Floor |
| `M` | Monster |
| `$` | Treasure |
| `†` | Weapon |
| `♥` | Health Potion |
| `>` | Exit |

## Monsters

| Monster | HP | Attack | Defense | Gold |
|---------|-----|--------|---------|------|
| Rat | 10 | 3 | 1 | 5 |
| Goblin | 20 | 6 | 2 | 15 |
| Orc | 40 | 10 | 5 | 30 |
| Troll | 60 | 15 | 8 | 50 |
| Dragon | 100 | 25 | 15 | 200 |

## Weapons

| Weapon | Attack Bonus | Special Effect |
|--------|-------------|----------------|
| Rusty Dagger | +2 | - |
| Short Sword | +5 | - |
| Battle Axe | +8 | - |
| Magic Staff | +10 | Arcane blast |
| Frost Blade | +12 | Freezing |
| Flaming Sword | +15 | Fire damage |

## Tips

- Collect health potions before engaging stronger monsters
- Better weapons appear on deeper dungeon levels
- You can flee from combat, but it's not guaranteed!
- The exit `>` appears in the bottom-right area of each level
