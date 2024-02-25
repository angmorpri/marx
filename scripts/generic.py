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

    import configparser

    cfg = configparser.RawConfigParser()
    cfg.read("C:/Users/angel/Desktop/marx/autoq.cfg", encoding="utf-8")
    for section in cfg.sections():
        print(section)
        for key, value in cfg[section].items():
            print(f"  {key}: {value}")
        print()
