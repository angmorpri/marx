# Python 3.10.11
# Creado: 24/01/2024
"""Para hacer pequeñas pruebas de código."""
import time

from marx.automation import Distribution
from marx.model import MarxAdapter
from marx.util import get_most_recent_db


if __name__ == "__main__":
    path = get_most_recent_db("G:/Mi unidad/MiBilletera Backups")
    print(">>> Usando: ", path)
    time.sleep(1)

    adapter = MarxAdapter(path)
    adapter.load()

    d = Distribution(adapter)
    d.source = "@Inversión"
    d.source.ratio = 70
    d.sinks.new(
        target="@Básicos",
        ratio=50,
        category="T11",
        concept="Cuota mensual",
    )
    d.sinks.new(
        target="@Personales",
        ratio=30,
        category="T11",
        concept="Cuota mensual",
    )
    d.sinks.new(
        target="@Reserva",
        ratio=20,
        category="T11",
        concept="Cuota mensual",
    )
    d.check(show=True)
