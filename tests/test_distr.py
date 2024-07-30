# Python 3.10.11
# Creado: 30/07/2024
"""Test de la clase Factory"""
import os
import sys

MARX_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__) + "/marx"))
sys.path.append(os.path.dirname(MARX_DIR))


from datetime import datetime
from pathlib import Path

from marx import Marx

TESTING_FILE = Path(__file__).parent / "data" / "Jul_04_2024_ExpensoDB"

AUTOQ_PATH = Path(__file__).parent / "files" / "autoquotas.toml"
AUTOI_PATH = Path(__file__).parent / "files" / "autoinvest.toml"

DEFAULT_DATE = datetime(2024, 6, 30)


if __name__ == "__main__":
    m = Marx()
    m.load(TESTING_FILE)

    m.distr(AUTOQ_PATH, DEFAULT_DATE)
    input()
    m.distr(AUTOI_PATH, DEFAULT_DATE)

    m.save()
