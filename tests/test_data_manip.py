# Python 3.10.11
# Creado: 15/07/2024
"""Test de la manipulación de datos"""
import os
import sys

MARX_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__) + "/marx"))
sys.path.append(os.path.dirname(MARX_DIR))

from datetime import datetime
from pathlib import Path

from marx import Marx
from marx.models import Event

TESTING_FILE = Path(__file__).parent / "Jul_04_2024_ExpensoDB"


def test_models():
    m = Marx()
    m.load(TESTING_FILE)
    data = m.data

    # Cuentas contables
    print("CUENTAS CONTABLES")
    data.accounts.head().show()
    print()
    for account in data.accounts.pull():
        print(account)
        print(account.serialize())
        print(account.repr_name)
        print()
    input("\n----------------------------------------------\n")

    # Categorías
    print("CATEGORÍAS")
    data.categories.head().show()
    print()
    for category in data.categories.pull():
        print(category)
        print(category.serialize())
        print()
    input("\n----------------------------------------------\n")

    # Eventos
    print("EVENTOS ACTIVOS")
    data.events.subset(status=1).head().show()
    print("EVENTOS PROGRAMADOS")
    data.events.subset(status=0).head().show()
    print("EVENTOS RECURRENTES")
    data.events.subset(type=Event.RECURRING).show()


def test_manip():
    m = Marx()
    m.load(TESTING_FILE)
    m.dbg_mode = True
    data = m.data

    # Cuentas contables
    #   - Nueva cuenta
    data.accounts.new(-1, "Prueba01", order=100, color="#151296")
    #   - Modificar cuenta
    data.accounts.subset(name="Básicos").order = 69
    #   - Modificar cuentas en bloque
    data.accounts.subset(lambda x: x.name.startswith("I")).color = "#069420"
    #   - Eliminar cuentas en bloque
    data.accounts.subset(disabled=True).delete()
    #   - Mostrar
    data.accounts.show()

    # Categorías
    #   - Nueva categoría
    data.categories.new(-1, "X00. Prueba01", 0, "#151296")
    #   - Modificar categoría
    data.categories.subset(code="A11").title = "SUELDOS"
    #   - Modificar categorías en bloque
    data.categories.subset(lambda x: x.code[2] == "3").color = "#000000"
    #  - Eliminar categorías en bloque
    data.categories.subset(lambda x: x.code[1] == "8").delete()
    #   - Mostrar
    data.categories.show()

    # Eventos
    #   - Nueva transacción
    res = data.events.new(
        -1,
        datetime(2024, 12, 15),
        10_000,
        data.categories.subset(code="X00").pullone(),
        "Dios",
        data.accounts.subset(name="Prueba01").pullone(),
        "Regalo del cielo",
    )
    res.show()

    return m.save()


if __name__ == "__main__":
    p = test_manip()
    print("\n\n>>> Se guarda en la ruta:", p)
