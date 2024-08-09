# Python 3.10.11
# Creado: 30/07/2024
"""Test de la clase PaycheckParser"""
import os
import sys

from numpy import sort

MARX_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__) + "/marx"))
sys.path.append(os.path.dirname(MARX_DIR))


import random
from datetime import datetime
from pathlib import Path
from pprint import pprint

from marx import Marx

TESTING_FILE = Path(__file__).parent / "data" / "Jul_04_2024_ExpensoDB"

CRITERIA_PATH = Path(__file__).parent / "files" / "paycheck.toml"
PAYCHECKS_DIR = Path("C:/Users/angel/OneDrive - Telefonica/Documentos/Nóminas/")

DEFAULT_DATE = datetime(2024, 6, 30)


if __name__ == "__main__":
    m = Marx()
    m.load(TESTING_FILE)

    if 0:
        report = m.paycheck_parse(PAYCHECKS_DIR / "06-2024.pdf", CRITERIA_PATH, DEFAULT_DATE)
        pprint(report, sort_dicts=False)

    if 1:
        paycheck = random.choice(list(PAYCHECKS_DIR.glob("*.pdf")))
        for year in ("2021", "2022", "2023", ""):
            subdir = PAYCHECKS_DIR / year
            for paycheck in subdir.glob("*.pdf"):
                if "SEPI" in paycheck.stem:
                    continue
                print(f"Procesando {paycheck}...")
                report = m.paycheck_parse(paycheck, CRITERIA_PATH, DEFAULT_DATE)
                pprint(report, sort_dicts=False)
                print()

    m.save()
