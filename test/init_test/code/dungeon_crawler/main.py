"""Entry point for the Dungeon Crawler game."""

import sys
from blessed import Terminal
from .game import Game


def main():
    """Main entry point for the game."""
    term = Terminal()
    game = Game()

    with term.fullscreen(), term.cbreak(), term.hidden_cursor():
        while game.running:
            # Render current state
            game.render()

            # Wait for input
            key = term.inkey(timeout=None)

            # Handle special keys
            if key.is_sequence:
                key_name = key.name
            else:
                key_name = str(key)

            # Handle input
            game.handle_input(key_name)

        # Show final screen
        game.render()

        # Wait for final keypress before exit
        term.inkey(timeout=None)

    print("\nThanks for playing Dungeon Crawler!")
    sys.exit(0)


if __name__ == "__main__":
    main()
