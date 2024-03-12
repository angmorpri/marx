# Python 3.10.11
# Creado: 11/03/2024
"""Para hacer pequeñas pruebas de código."""
import os
import sys

MARX_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__) + "/marx"))
sys.path.append(os.path.dirname(MARX_DIR))


import time
from datetime import datetime
from pathlib import Path

from marx.model import MarxAdapter
from marx.util import get_most_recent_db
from marx.util.excel import ExcelManager


if __name__ == "__main__":
    path = get_most_recent_db("G:/Mi unidad/MiBilletera Backups")
    print(">>> Usando: ", path)
    time.sleep(0.25)
    adapter = MarxAdapter(path)
    adapter.load()

    loans = {}
    for event in adapter.suite.events.search(
        lambda ev: ev.category.code in ("B14", "A23"),
        lambda ev: ev.date.year > 2021,
        status="closed",
    ):
        if event.category.code == "B14":
            if event.dest not in loans:
                loans[event.dest] = {
                    "payee_events": [],
                    "payer_events": [],
                    "base_total": 0,
                    "left_total": 0,
                }
            loans[event.dest]["payee_events"].append(event)
            loans[event.dest]["base_total"] += event.amount
            loans[event.dest]["left_total"] += event.amount
        elif event.category.code == "A23":
            for payee in loans:
                if event.orig in payee and loans[payee]["left_total"] > 0:
                    loans[payee]["payer_events"].append(event)
                    loans[payee]["left_total"] -= event.amount
                    break

    print(">>> Préstamos:")
    for payee, data in loans.items():
        print(f"{payee}: {data['base_total']:.2f} - {data['left_total']:.2f}")
        for event in data["payee_events"]:
            print(f"  - {event}")
        for event in data["payer_events"]:
            print(f"  + {event}")
        print()
        input()
