# Creado: 24/01/2025
"""Test de la nueva gestión de categorías, con el nuevo parámetro 'type'"""
import os
import sys

MARX_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__) + "/marx"))
sys.path.append(os.path.dirname(MARX_DIR))


from pathlib import Path

from marx import Marx
from marx.models import Category

TESTING_FILE = Path(__file__).parent / "data" / "Jul_04_2024_ExpensoDB"


def test_all():
    """Pruebas del nuevo sistema de categorías

    Se probará:
    - Carga de datos
    - Mostrar categorías
    - Modificar categoría
    - Crear nueva categoría
    - Guardar datos

    """

    m = Marx()
    m.load(TESTING_FILE)
    data = m.data

    data.categories.sort().show()
    input()

    data.categories.subset(code="A11").update(title="PRUEBA")
    data.categories.sort().show()
    input()

    data.categories.new(-1, "X99. NUEVO INGRESO", Category.INCOME)
    data.categories.new(-1, "Y99. NUEVO GASTO", Category.EXPENSE)
    data.categories.new(-1, "Z99. NUEVA TRANSFERENCIA", Category.TRANSFER)
    data.categories.sort().show()
    input()

    res = m.save()
    print("\n\n>>> Se guarda en la ruta:", res)


if __name__ == "__main__":
    test_all()
