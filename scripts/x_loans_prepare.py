# Python 3.10.11
# Creado: 13/03/2024
"""Genera un archivo Excel para asignar etiquetas a los eventos de préstamo 
relacionados.

"""
import os
import sys

MARX_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__) + "/marx"))
sys.path.append(os.path.dirname(MARX_DIR))


import time
from pathlib import Path

import openpyxl

from marx.model import MarxMapper
from marx.util import get_most_recent_db


def prepare_excel(adapter: MarxMapper, dir: str | Path) -> None:
    """Excel con los eventos de préstamo relacionados."""
    output = Path(dir) / f"loans_{int(time.time())}.xlsx"
    wb = openpyxl.Workbook()
    sheet = wb.active
    sheet.title = "Préstamos"
    sheet.append(
        (
            "ID",
            "Fecha",
            "Cantidad",
            "Origen",
            "Destino",
            "Categoría",
            "Concepto",
            "Detalle",
            "Etiqueta",
        )
    )
    for event in adapter.struct.events.search(
        lambda ev: ev.category.code in ("B14", "A23"),
        lambda ev: ev.date.year > 2021,
        status="closed",
    ):
        sheet.append(
            (
                str(event.id),
                event.date.strftime("%d/%m/%Y"),
                event.amount,
                event.orig if isinstance(event.orig, str) else event.orig.name,
                event.dest if isinstance(event.dest, str) else event.dest.name,
                event.category.code,
                event.concept,
                event.details,
                "",
            )
        )
    wb.save(output)


if __name__ == "__main__":
    path = get_most_recent_db("G:/Mi unidad/MiBilletera Backups")
    print(">>> Usando: ", path)
    time.sleep(0.25)
    adapter = MarxMapper(path)
    adapter.load()
    prepare_excel(adapter, Path(__file__).parent.parent / "out")
    print("HECHO")
