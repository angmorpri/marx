# Python 3.10.11
# Creado: 24/01/2024
"""Para hacer pequeñas pruebas de código."""
import os
import sys

MARX_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__) + "/marx"))
sys.path.append(os.path.dirname(MARX_DIR))


from pathlib import Path

from marx import Marx
from marx.util import Pathfinder


CONFIG_PATH = Path(__file__).parent.parent / "config" / "paths.cfg"


if __name__ == "__main__":
    paths = Pathfinder(CONFIG_PATH)
    for key in (
        "sources-dir",
        "wages-dir",
        "user-dir",
        "autoinvest-config",
        "autoquotas-config",
        "wageparser-config",
    ):
        print(f"{key}: {paths.request(key)}")
