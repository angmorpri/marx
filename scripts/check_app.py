# Python 3.10.11
# Creado: 31/01/2024
"""Calcula el capital en cada cuenta para comparar con la app y validar."""
from collections import defaultdict
import os
import sys

MARX_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__) + "/marx"))
sys.path.append(os.path.dirname(MARX_DIR))


from marx.model import MarxMapper
from marx.util import get_most_recent_db


if __name__ == "__main__":
    source = get_most_recent_db("G:/Mi unidad/MiBilletera Backups/")
    # source = "G:/Mi unidad/MiBilletera Backups/MOD_Ene_31_2024_ExpensoDB.db"
    adapter = MarxMapper(source)
    adapter.load()
    budgets = defaultdict(int)
    for event in adapter.struct.events.search(status="closed"):
        for account, sign in zip((event.orig, event.dest), (-1, 1)):
            if isinstance(account, str) or account.unknown:
                continue
            budgets[account.name] += sign * event.amount
    for name, amount in budgets.items():
        print(f"{name:20}: {amount:10.2f}")
    print("HECHO")
