# Python 3.10.11
# Creado: 11/03/2024
"""Calcula el balance general para una fecha dada."""

import time
from datetime import datetime
from pathlib import Path

from marx.model import MarxMapper
from marx.util import get_most_recent_db
from marx.reporting import Balance


DMC_PATH = "C:/Users/angel/Documents/Documento Maestro de Contabilidad.xlsx"
DMC_SHEET = "Balance"


if __name__ == "__main__":
    print("[BALANCE GENERAL]")
    path = get_most_recent_db("G:/Mi unidad/MiBilletera Backups")
    print("Usando: ", path)
    time.sleep(0.25)
    adapter = MarxMapper(path)
    adapter.load()

    # Fecha(s)
    dates = None
    while not dates:
        dates = input(
            "Fecha/s de los eventos (formato dd/mm/yyyy).\n"
            "Si se incluyen varios, deben separarse mediante un punto y coma (';').\n"
            ">>> "
        )
        if not dates:
            dates = [datetime.now()]
        else:
            _aux = []
            for date in dates.split(";"):
                try:
                    _aux.append(datetime.strptime(date.strip(), "%d/%m/%Y"))
                except ValueError:
                    print(f"Fecha inválida: {date}")
                    dates = None
                    break
            else:
                dates = _aux

    # Balance
    balance = Balance(adapter.data)
    table = balance.build(*dates)
    out = balance.report(table, format="excel", output=DMC_PATH, sheet=DMC_SHEET)
    print(">>>", out)
