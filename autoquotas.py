# Python 3.10.11
# Creado: 24/02/2024
"""Genera automáticamente los repartos de cuotas mensuales."""
import time
from datetime import datetime
from pathlib import Path

from marx.automation import Distribution
from marx.model import MarxAdapter
from marx.util import get_most_recent_db, parse_nested_cfg


CFG_PATH = Path(__file__).parent / "config" / "autoq.cfg"


if __name__ == "__main__":
    print("[AUTO CUOTAS MENSUALES]")
    path = get_most_recent_db("G:/Mi unidad/MiBilletera Backups")
    print("Usando: ", path)
    time.sleep(0.25)
    adapter = MarxAdapter(path)
    adapter.load()

    # Fecha
    date = None
    while not date:
        date = input("Fecha de los eventos (formato dd/mm/yyyy): ")
        if not date:
            date = datetime.now()
        else:
            try:
                date = datetime.strptime(date, "%d/%m/%Y")
            except ValueError:
                print("Fecha inválida")

    # Configuración
    d = Distribution.from_cfg(adapter.suite, CFG_PATH)
    d.prepare(verbose=True)
    d.run(date=date)

    # Guardar
    path = adapter.save(prefix="AUTOQ")
    print(f"Distribución realizada y resultado almacenado en {path!s}")
