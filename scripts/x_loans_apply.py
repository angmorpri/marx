# Python 3.10.11
# Creado: 13/03/2024
"""Aplica los cambios en la Excel indicada."""
import os
import sys

MARX_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__) + "/marx"))
sys.path.append(os.path.dirname(MARX_DIR))


import time
from pathlib import Path

import openpyxl

from marx.model import MarxMapper
from marx.util import get_most_recent_db


def apply_excel(adapter: MarxMapper, dir: str | Path) -> None:
    """Aplica los cambios en la Excel indicada."""
    wb = openpyxl.load_workbook(dir)
    sheet = wb.active
    for id, *_, tag in sheet.iter_rows(min_row=2, values_only=True):
        # ID
        if isinstance(id, str):
            id = complex(id) if "j" in id else int(id)
        else:
            id = int(id)
        # Evento base
        event = adapter.data.events[id]
        if not event:
            raise ValueError(f"Evento {id} no encontrado.")
        # Se añade la etiqueta a los detalles del evento
        if tag:
            event.details += f"\n[{tag}]"
            event.details = event.details.strip()
            print(f"[{id}] Etiqueta añadida: {tag}")
    wb.save(dir)


if __name__ == "__main__":
    path = get_most_recent_db("G:/Mi unidad/MiBilletera Backups")
    print(">>> Usando: ", path)
    time.sleep(0.25)
    adapter = MarxMapper(path)
    adapter.load()

    apply_excel(adapter, Path(__file__).parent.parent / "out" / "loans_1710286039.xlsx")
    out = adapter.save()

    print(">>> Cambios aplicados.", out)
