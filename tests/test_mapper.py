# Python 3.10.11
# Creado: 08/07/2024
"""Test de la clase Factory"""
import os
import sys

MARX_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__) + "/marx"))
sys.path.append(os.path.dirname(MARX_DIR))


from pathlib import Path

from marx import Marx

TESTING_FILE = Path(__file__).parent / "Jul_04_2024_ExpensoDB"


def test_load_show():
    m = Marx()
    m.load(TESTING_FILE)
    data = m.data

    data.accounts.show()
    input()
    data.categories.show()
    input()
    data.events.show()
    input()


def test_save():
    m = Marx()
    m.dbg_mode = True
    m.load(TESTING_FILE)
    data = m.data

    data.accounts.new(-1, "Prueba01", 69)

    res = m.save()
    print("\n\n>>> Se guarda en la ruta:", res)


if __name__ == "__main__":
    # test_load_show()
    test_save()
