"""
main.py
Entry point. Initializes the engine and starts the game loop.
This file does nothing except start the engine — all logic lives elsewhere.
Run from the survival-game/ directory: python main.py
"""

import sys
import logging
import traceback
from game.core.engine import Engine

logging.basicConfig(level=logging.WARNING,
                    format="[%(levelname)s] %(name)s: %(message)s")


if __name__ == "__main__":
    try:
        engine = Engine()
        engine.run()
    except ImportError as e:
        print(f"\n[ERROR] Missing dependency: {e}")
        print("Fix:  pip install -r requirements.txt\n")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"\n[ERROR] Missing file: {e}")
        print("Make sure you are running from the survival-game/ directory.\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected crash: {e}")
        traceback.print_exc()
        sys.exit(1)
