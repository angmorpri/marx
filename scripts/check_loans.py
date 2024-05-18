# Python 3.10.11
# Creado: 11/03/2024
"""Para hacer pequeñas pruebas de código."""
import os
import sys

MARX_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__) + "/marx"))
sys.path.append(os.path.dirname(MARX_DIR))


import time
import re
from datetime import datetime
from pathlib import Path

from marx.model import MarxMapper
from marx.util import get_most_recent_db
from marx.util.excel import ExcelManager


def find_tags(text: str) -> list[str]:
    """Encuentra todas las etiquetas en un texto."""
    pattern = r"\[([^\[\]]+)\]"
    return re.findall(pattern, text)


def find_loans(adapter: MarxMapper) -> None:
    loans = {}
    for event in adapter.struct.events.search(
        lambda ev: ev.category.code in ("B14", "A23"),
        status="closed",
    ):
        if tags := find_tags(event.details):
            tag = tags[0]
            if tag not in loans:
                loans[tag] = {
                    "loans": [],
                    "payments": [],
                    "base_total": 0,
                    "left_total": 0,
                }
            if event.category.code == "B14":
                loans[tag]["loans"].append(event)
                loans[tag]["base_total"] += event.amount
                loans[tag]["left_total"] += event.amount
            elif event.category.code == "A23":
                loans[tag]["payments"].append(event)
                loans[tag]["left_total"] -= event.amount

    print(">>> Préstamos:")
    for tag, loan in loans.items():
        print(f"  - {tag}:")
        print(f"    - Base: {loan['base_total']}")
        print(f"    - Restante: {loan['left_total']}")
        print(f"    - Préstamos:")
        for event in loan["loans"]:
            print(f"      - {event}")
        print(f"    - Pagos:")
        for event in loan["payments"]:
            print(f"      - {event}")
        print()
        input()


if __name__ == "__main__":
    path = get_most_recent_db("G:/Mi unidad/MiBilletera Backups")
    print(">>> Usando: ", path)
    time.sleep(0.25)
    adapter = MarxMapper(path)
    adapter.load()

    find_loans(adapter)
