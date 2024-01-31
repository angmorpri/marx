# Python 3.10.11
# Creado: 31/01/2024
"""Genera un archivo Excel para cambiar las categorías de los eventos."""
import os
import sys

MARX_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__) + "/marx"))
sys.path.append(os.path.dirname(MARX_DIR))


import time
from pathlib import Path

import openpyxl

from marx.model import MarxAdapter
from marx.util import get_most_recent_db


MARX_AT_DESKTOP = Path("C:/Users/angel/Desktop/marx")


def apply_excel(adapter: MarxAdapter, dir: str | Path) -> None:
    """Aplica los cambios en el archivo Excel especificado.

    Aplica todo cambio indicado en "Nueva categoría", y también si hay ajustes
    en "Concepto".

    """
    wb = openpyxl.load_workbook(dir)
    income_sheet = wb["Ingresos"]
    # expense_sheet = wb["Gastos"]
    transfer_sheet = wb["Traslados"]
    for sheet in (income_sheet, transfer_sheet):
        for id, *row in sheet.iter_rows(min_row=2, values_only=True):
            if isinstance(id, str):
                id = complex(id) if "j" in id else int(id)
            else:
                id = int(id)
            event = adapter.suite.events[id]
            if not event:
                raise ValueError(f"Evento {id} no encontrado ({row})")
            _, _, concept, _, new_category_id, *_ = row
            if concept != event.concept:
                print(f"[{id}] Concepto cambiado: {event.concept} -> {concept}")
                event.concept = concept
            if new_category_id:
                new_category = adapter.suite.categories[new_category_id]
                if not new_category:
                    raise ValueError(f"[{id}] Categoría no encontrada: {new_category_id}")
                else:
                    print(f"[{id}] Categoría cambiada: {event.category} -> {new_category}")
                    event.category = new_category
        print("\n----------------------------------------------\n")


if __name__ == "__main__":
    source = get_most_recent_db("G:/Mi unidad/MiBilletera Backups")
    print(">>> Usando: ", source)
    time.sleep(1)

    adapter = MarxAdapter(source)
    adapter.load()
    apply_excel(adapter, MARX_AT_DESKTOP / "recat_1706724239.xlsx")

    # Aprovechamos para eliminar categorías que empiecen por 'XXX'
    adapter.suite.categories.search(code="XXX").delete()

    adapter.save()
    print("HECHO")
