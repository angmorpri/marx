# Python 3.10.11
# Creado: 03/08/2024
"""Test del cliente"""
import os
import sys

MARX_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__) + "/marx"))
sys.path.append(os.path.dirname(MARX_DIR))


from datetime import datetime
from pathlib import Path

from marx.cli import MarxCLI


USERCONFIG = Path(__file__).parent / "files" / "marxuserconfig.toml"
TESTING_DB = Path(__file__).parent / "data" / "Jul_04_2024_ExpensoDB"


def test_load():
    marxcli = MarxCLI(USERCONFIG)

    print(">>> load")
    marxcli.load()

    print(">>> load auto")
    marxcli.load("auto")

    print(">>> load pick")
    marxcli.load("pick")

    print(">>> load MOD_Ago_03_2024_ExpensoDB")
    marxcli.load("MOD_Ago_03_2024_ExpensoDB")

    print(">>> load C:/Users/angel/Programación/projects/marx/tests/data/Jul_04_2024_ExpensoDB")
    marxcli.load("C:/Users/angel/Programación/projects/marx/tests/data/Jul_04_2024_ExpensoDB")


def test_save():
    marxcli = MarxCLI(USERCONFIG)

    print(">>> load TESTING_DB")
    marxcli.load(TESTING_DB)

    print(">>> save")
    marxcli.save()

    print(">>> save auto")
    marxcli.save("auto")

    print(">>> save pick")
    marxcli.save("pick")

    print(">>> save TESTREL_Jul_04_2024_ExpensoDB.db")
    marxcli.save("TESTREL_Jul_04_2024_ExpensoDB.db")

    print(">>> save TESTRELPREFIX_?.db")
    marxcli.save("TESTRELPREFIX_?.db")

    print(">>> save C:/Users/angel/Desktop/TESTABS_Jul_04_2024_ExpensoDB.db")
    marxcli.save("C:/Users/angel/Desktop/TESTABS_Jul_04_2024_ExpensoDB.db")

    print(">>> save C:/Users/angel/Desktop/TESTABSPREFIX_?.db")
    marxcli.save("C:/Users/angel/Desktop/TESTABSPREFIX_?.db")


def test_distr():
    marxcli = MarxCLI(USERCONFIG)
    print(">>> load <TESTING_DB>")
    marxcli.load(TESTING_DB)
    marxcli.marx.data.events.new(
        id=-1,
        date=datetime(2024, 7, 3),
        amount=1000,
        category=marxcli.marx.data.categories.subset(code="A11").pullone(),
        orig="Dios",
        dest=marxcli.marx.data.accounts.subset(name="Ingresos").pullone(),
        concept="Para pruebas",
    )

    print(">>> autoquotas")
    marxcli.autoquotas()

    print(">>> autoinvest 2024-12-15")
    marxcli.autoinvest("2024-12-15")

    print(
        ">>> autoinvest C:/Users/angel/Programación/projects/marx/tests/files/autoinvest2.toml 28/10/2024"
    )
    marxcli.distr(
        "C:/Users/angel/Programación/projects/marx/tests/files/autoinvest2.toml", "28/10/2024"
    )

    print(">>> save")
    marxcli.save()


def test_paychecks():
    marxcli = MarxCLI(USERCONFIG)
    marxcli = MarxCLI(USERCONFIG)
    print(">>> load <TESTING_DB>")
    marxcli.load(TESTING_DB)

    print(">>> paycheck")
    marxcli.paycheck()


if __name__ == "__main__":
    test_paychecks()
