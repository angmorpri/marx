# Python 3.10.11
# Creado: 23/07/2024
"""Reorganización de categorías de julio de 2024"""
import os
import sys

MARX_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__) + "/marx"))
sys.path.append(os.path.dirname(MARX_DIR))


from pathlib import Path

from marx import Marx


TARGET_FILE = Path(__file__).parent / "Jul_04_2024_ExpensoDB"


def check_split():
    m = Marx()
    m.load(TARGET_FILE)
    data = m.data

    # A23. Devoluciones
    data.events.subset(lambda x: "A23" in x.category).sort().show()

    # A30. Rendimiento financiero
    data.events.subset(lambda x: "A30" in x.category).sort().show()


def do_income(m: Marx):
    cats = m.data.categories

    # Renombramientos
    cats.subset(code="A24").code = "A31"  # Préstamos
    cats.subset(code="A30").name = "A33. Intereses y dividendos"

    # Nuevas categorías
    deudas = cats.new(-1, "A32. Deudas").pullone()
    rend = cats.new(-1, "A34. Rendimientos de ventas").pullone()

    # Ajustar eventos para las nuevas categorías y los splits
    ids = [3517, 3434, 3416, 3196, 3220]
    m.data.events.subset(lambda x: x.id in ids).category = deudas

    # Prueba
    cats.subset(lambda x: x.code.startswith("A")).sort().show()
    m.data.events.subset(lambda x: "A23" in x.category).sort().show()
    m.data.events.subset(lambda x: "A32" in x.category).sort().show()


def do_expenses(m: Marx):
    cats = m.data.categories
    
    # Alimentación + Consumibles
    alim = cats.subset(code="B31").pullone()
    m.data.events.subset(lambda x: "B32" in x.category).category = alim
    cats.subset(code="B32").delete()
    
    # Compras + Servicios generales
    compras = cats.subset(code="B41").pullone()
    m.data.events.subset(lambda x: "B42" in x.category).category = compras
    cats.subset(code="B41").name = "B41. Compras y servicios generales"
    cats.subset(code="B42").delete()
    
    # Renombramientos
    renaming = {
        "B11": "I01. Impuestos",
        "B12": "B63. Comisiones",
        "B13": "B62. Deudas",
        "B14": "B61. Préstamos",
        "B15": "X11. Impago de préstamos",
        "B16": "B64. Pérdidas de ventas",
        
        "B21": "B11. Vivienda",
        "B22": "B12. Gastos médicos y cuidado personal",
        "B23": "B13. Deportes",
        "B24": "B14. Formación",
        
        "B31": "B21. Alimentación",
        "B33": "B22. Antojos",
        "B34": "B23. Alcohol y drogas",
        "B35": "B24. Restaurantes y bares",
    }


if __name__ == "__main__":
    m = Marx()
    m.load(TARGET_FILE)

    # check_split()
    do_income(m)
    do_expenses(m)

    m.save()
