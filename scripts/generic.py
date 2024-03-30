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

from marx.api import MarxAPI


if __name__ == "__main__":
    api = MarxAPI()
    print("Usando: ", api.current_source)
    print()
    print("Autoquotas")
    api.autoquotas()
    print("Autoinvest")
    api.autoinvest()
    print("Wage Parser")
    api.wageparser("03-2024")
    print("OK")
