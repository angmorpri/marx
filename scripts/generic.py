# Python 3.10.11
# Creado: 24/01/2024
"""Para hacer pequeñas pruebas de código."""
import os
import sys

MARX_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__) + "/marx"))
sys.path.append(os.path.dirname(MARX_DIR))


import time
from datetime import datetime
from pathlib import Path

from marx.model import MarxAdapter
from marx.util import get_most_recent_db
from marx.reporting import Balance


if __name__ == "__main__":
    # path = get_most_recent_db("G:/Mi unidad/MiBilletera Backups")
    path = Path(__file__).parent.parent / "local" / "Mar_06_2024_ExpensoDB"
    print(">>> Usando: ", path)
    time.sleep(0.25)
    adapter = MarxAdapter(path)
    adapter.load()

    balance = Balance(adapter.suite)
    table = balance.build(
        datetime(2022, 1, 8),
        datetime(2023, 1, 8),
        datetime(2024, 1, 8),
    )
    output = Path(__file__).parent.parent / "local" / "balance-2020-2024-fix.xlsx"
    if output.exists():
        output.unlink()
    out = balance.report(table, format="excel", output=output)
    print(">>>", out)
