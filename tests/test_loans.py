# Python 3.10.11
# Creado: 30/07/2024
"""Test de la clase LoansHandler"""
import os
import sys


MARX_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__) + "/marx"))
sys.path.append(os.path.dirname(MARX_DIR))


from datetime import datetime
from pathlib import Path
from pprint import pprint

from marx import Marx
from marx.automation import LoansHandler
from marx.mappers import MarxMapper

TESTING_FILE = Path(__file__).parent / "data" / "Ago_16_2024_ExpensoDB"

DEFAULT_DATE = datetime(2024, 8, 30)


def raw_test():
    mapper = MarxMapper(TESTING_FILE)
    data = mapper.load()
    loans = LoansHandler(data)
    for loan in loans.find(datetime(2024, 2, 1)):
        print(loan)
        loan.show()
        for event in loan.events:
            print(" -", event.pullone())
        print()


if __name__ == "__main__":

    if 1:
        raw_test()

    if 0:
        m = Marx()
        m.load(TESTING_FILE)

        res = m.loans_list(DEFAULT_DATE)
        pprint(res, sort_dicts=False)
        input()

        res = m.loans_default("THORLT")
        pprint(res, sort_dicts=False)
        input()

        pprint(m.loans_list(DEFAULT_DATE), sort_dicts=False)

        m.save()
