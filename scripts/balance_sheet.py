# Python 3.10.11
# Creado: 31/01/2024
"""Muestra el balance general a una fecha determinada."""
import os
import sys

MARX_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__) + "/marx"))
sys.path.append(os.path.dirname(MARX_DIR))


import time
from collections import Counter
from datetime import datetime, timedelta

from marx.model import MarxAdapter
from marx.util import get_most_recent_db


CURRENTS = ("Metálico", "Ingresos", "Básicos", "Personales", "UpGourmet")
RESERVE = ("Ahorro", "Reserva")


def balance(adapter: MarxAdapter, date: datetime | str | None = None) -> None:
    """Muestra el balance general a una fecha determinada."""
    # Fecha de corte
    if date is None:
        date = datetime.now() + timedelta(days=1)
    elif isinstance(date, str):
        date = datetime.strptime(date, "%Y-%m-%d")

    # Balance
    assets = {
        "Corriente": Counter(),
        "Reserva": Counter(),
        "Inversión": Counter(),
    }
    for event in adapter.suite.events.search(lambda x: x.date < date, status="closed"):
        for account, sign in zip((event.orig, event.dest), (-1, 1)):
            if isinstance(account, str) or account.unknown:
                continue
            if account.name in CURRENTS:
                assets["Corriente"][account.name] += sign * event.amount
            elif account.name in RESERVE:
                assets["Reserva"][account.name] += sign * event.amount
            elif event.type != 0:
                raise ValueError(f"Cuenta de inversión no reconocida: {event}")
            else:
                assets["Inversión"][event.category.title] += sign * event.amount

    # Imprimir
    for key, value in assets.items():
        print(f"{key:.<29}{sum(value.values()):.>10.2f} €")
        for name, amount in value.items():
            print(f"    {name:.<25}{amount:.>10.2f} €")
        print()
    print("Total: ", sum(sum(value.values()) for value in assets.values()), "€")


if __name__ == "__main__":
    # source = "G:/Mi unidad/MiBilletera Backups/MOD_Ene_31_2024_ExpensoDB.db"
    source = get_most_recent_db("G:/Mi unidad/MiBilletera Backups")
    print(">>> Usando: ", source)
    time.sleep(1)

    adapter = MarxAdapter(source)
    adapter.load()

    balance(adapter, "2023-01-01")
