# Python 3.10.11
# Creado: 24/01/2024
"""Para hacer pequeñas pruebas de código."""
import time
from pprint import pprint

from marx.model import RawAdapter, MarxAdapter
from marx.util import get_most_recent_db


if __name__ == "__main__":
    path = get_most_recent_db("G:/Mi unidad/MiBilletera Backups")
    print(">>> Usando: ", path)
    time.sleep(1)
