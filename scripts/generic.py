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
from pprint import pprint

from marx import Marx

IPATH = Path("C:/Users/angel/Desktop/autoi.cfg")

if __name__ == "__main__":
    api = Marx()
    output = api.balance(datetime(2023, 10, 1), datetime(2024, 4, 1), "2w")
    print(">>>", output)
