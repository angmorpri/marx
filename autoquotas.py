# Python 3.10.11
# Creado: 24/02/2024
"""Genera automáticamente los repartos de cuotas mensuales."""
import os
import sys

MARX_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__) + "/marx"))
sys.path.append(os.path.dirname(MARX_DIR))


import time

from marx.automation import Distribution
from marx.model import MarxAdapter
from marx.util import get_most_recent_db


DISTROS = [
    {
        "target": "@Básicos",
        "ratio": 50,
        "category": "T11",
        "concept": "Cuota mensual",
        "details": "(50%)",
    },
    {
        "target": "@Personales",
        "ratio": 30,
        "category": "T11",
        "concept": "Cuota mensual",
        "details": "(30%)",
    },
    {
        "target": "@Reserva",
        "ratio": 20,
        "category": "T11",
        "concept": "Cuota mensual",
        "details": "(20%)",
    },
]


if __name__ == "__main__":
    path = get_most_recent_db("G:/Mi unidad/MiBilletera Backups")
    print(">>> Usando: ", path)
    time.sleep(1)

    adapter = MarxAdapter(path)
    adapter.load()

    d = Distribution(adapter)
    d.source = "@Ingresos"
    for distro in DISTROS:
        d.sinks.new(**distro)
    d.check(show=True)
    d.run()

    adapter.save(prefix="AUTOQ")
