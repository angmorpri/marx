# Python 3.10.11
# Creado: 24/02/2024
"""Genera automáticamente los repartos de inversión."""
import os
import sys

MARX_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__) + "/marx"))
sys.path.append(os.path.dirname(MARX_DIR))


import configparser
import time
from pathlib import Path

from marx.automation import Distribution
from marx.model import MarxAdapter
from marx.util import get_most_recent_db


CFG_PATH = Path(__file__).parent / "autoi.cfg"


DISTROS = [
    {
        "target": "@Inversión",
        "amount": 230,
        "category": "T24",
        "concept": "MyInvestor Indie",
    },
    {
        "target": "@Inversión",
        "amount": 50,
        "category": "T24",
        "concept": "Finanbest Profile Yellow",
    },
    {
        "target": "@Inversión",
        "amount": 20,
        "category": "T23",
        "concept": "MyInvestor Value",
    },
]


if __name__ == "__main__":
    path = get_most_recent_db("G:/Mi unidad/MiBilletera Backups")
    print(">>> Usando: ", path)
    time.sleep(1)

    adapter = MarxAdapter(path)
    adapter.load()

    d = Distribution(adapter)
    d.source = "@Reserva"
    for distro in DISTROS:
        d.sinks.new(**distro)
    d.check(show=True)
    d.run()

    adapter.save(prefix="AUTOV")
