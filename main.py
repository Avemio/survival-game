"""
main.py
Entry point. Initializes the engine and starts the game loop.
This file does nothing except start the engine — all logic lives elsewhere.
Run from the survival-game/ directory: python main.py
"""

from game.core.engine import Engine


if __name__ == "__main__":
    engine = Engine()
    engine.run()
