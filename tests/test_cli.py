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
    print(">>> load <TESTING_DB>")
    marxcli.load(TESTING_DB)

    print(">>> paycheck")
    marxcli.paycheck()

    print(">>> paycheck 02-2024-X.pdf")
    marxcli.paycheck("02-2024-X.pdf")

    print(">>> paycheck C:/Users/angel/OneDrive - Telefonica/Documentos/Nóminas/01-2024.pdf")
    marxcli.paycheck("C:/Users/angel/OneDrive - Telefonica/Documentos/Nóminas/01-2024.pdf")

    print(
        ">>> paycheck 07-2024.pdf C:/Users/angel/Programación/projects/marx/tests/files/paycheck.toml 20241010"
    )
    marxcli.paycheck(
        "07-2024.pdf",
        "C:/Users/angel/Programación/projects/marx/tests/files/paycheck.toml",
        "20241010",
    )

    print(">>> save")
    marxcli.save()


def test_loans():
    marxcli = MarxCLI(USERCONFIG)
    print(">>> load <TESTING_DB>")
    marxcli.load(TESTING_DB)

    print(">>> loans")
    marxcli.loans_list()

    print(">>> loans 2024-01-01")
    marxcli.loans_list("2024-01-01")

    print(">>> loans default THORLT")
    marxcli.loans_default("THORLT")

    print(">>> loans")
    marxcli.loans_list()


if __name__ == "__main__":
    test_loans()
