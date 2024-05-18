# Python 3.10.11
# Creado: 26/02/2024
"""Test para WageParser."""
import os
import sys
from tkinter.filedialog import askopenfilename

MARX_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__) + "/marx"))
sys.path.append(os.path.dirname(MARX_DIR))


from datetime import datetime

from marx.automation import WageParser
from marx.model import MarxMapper
from marx.util import get_most_recent_db


WAGES_DIR = r"C:\Users\angel\OneDrive - Telefonica\Documentos\Nóminas"


if __name__ == "__main__":
    print("[WAGE PARSER TEST]")
    path = get_most_recent_db("G:/Mi unidad/MiBilletera Backups")
    print("Usando: ", path)
    adapter = MarxMapper(path)
    adapter.load()

    # WageParser
    wp = WageParser(adapter)
    for wage in wp.iter_all(dir=WAGES_DIR):
        print(wage.stem)
        wp.parse(wage, verbose=True)
        print()

    print("\nPruebas realizadas", path)
