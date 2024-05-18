# Python 3.10.11
# Creado: 24/01/2024
"""Para hacer pequeñas pruebas de código."""
import os
import sys

MARX_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__) + "/marx"))
sys.path.append(os.path.dirname(MARX_DIR))


import time
from datetime import datetime
from pathlib import Path

from marx.model import MarxMapper, find_loans
from marx.util import get_most_recent_db
from marx.reporting import Balance


if __name__ == "__main__":
    print("[FIX LOANS]")
    path = get_most_recent_db("G:/Mi unidad/MiBilletera Backups")
    print(">>> Usando: ", path)
    time.sleep(0.25)
    adapter = MarxMapper(path)
    adapter.load()

    # LOANS
    print(">>> Préstamos:")
    loans = find_loans(adapter.struct)
    for loan in loans.values():
        print(loan)
    print()

    # Fix
    print(">>> Se ajusta uno para crear un impago.")
    default, fix = loans["THORLT"].generate_default(15)
    adapter.struct.events.add(default)
    adapter.struct.events.add(fix)
    out = adapter.save()
    print()

    # Recalcular préstamos para garantizar que han cambiado
    print(">>> Nuevo estado de los préstamos:")
    loans = find_loans(adapter.struct)
    for loan in loans.values():
        print(loan)
    print()

    print(">>> Hecho", out)
