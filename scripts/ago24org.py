# Python 3.10.11
# Creado: 23/07/2024
"""Reorganización de categorías de julio de 2024"""
import os
import sys

MARX_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__) + "/marx"))
sys.path.append(os.path.dirname(MARX_DIR))


from datetime import datetime
from pathlib import Path

from marx import Marx


TARGET_FILE = Path("G:/Mi unidad/MiBilletera Backups/Ago_10_2024_ExpensoDB")


def do_income(m: Marx):
    cats = m.data.categories

    print("A24. Préstamos --> A31. Préstamos")
    cats.subset(code="A24").code = "A31"

    print("NEW A32. Deudas")
    deudas = cats.new(-1, "A32. Deudas").pullone()

    print("A30. Rendimiento financiero --> A33. Intereses y dividendos")
    cats.subset(code="A30").name = "A33. Intereses y dividendos"

    print("NEW A34. Ganancias por ventas")
    rend = cats.new(-1, "A34. Ganancias por ventas").pullone()

    print("A23. Devoluciones /-> A23. Devoluciones + A32. Deudas")
    events = []
    for _, loan in m.loans_list(datetime.now()).items():
        events += [e["id"] for e in loan["events"] if e["category"]["code"] == "A23"]
    m.data.events.subset(lambda x: x.id in events).category = deudas
    m.data.events.subset(lambda x: x.id in events).sort().show()
    print()
    cats.subset(lambda x: x.code.startswith("A")).sort().show()


def do_expenses(m: Marx):
    cats = m.data.categories

    # Alimentación + Consumibles
    print("B31. Alimentación + B32. Consumibles --> B31. Comida")
    alim = cats.subset(code="B31")
    alim.name = "B31. Comida"
    m.data.events.subset(lambda x: "B32" in x.category).category = alim.pullone()
    cats.subset(code="B32").delete()

    # Compras + Servicios generales
    print("B41. Compras + B42. Servicios generales --> B41. Compras y servicios generales")
    compras = cats.subset(code="B41")
    compras.name = "B41. Compras y servicios generales"
    m.data.events.subset(lambda x: "B42" in x.category).category = compras.pullone()
    cats.subset(code="B42").delete()

    # Renombramientos
    renaming = {
        # [B90] Otros gastos
        "B11": "B91. Impuestos",
        "B91": "B98. Ajustes",
        "B92": "B99. Otros gastos",
        # [B60] Gastos financieros
        "B12": "B63. Comisiones",
        "B13": "B62. Deudas",
        "B14": "B61. Préstamos",
        "B16": "B64. Pérdidas por ventas",
        # [B10] Gastos vitales
        "B21": "B11. Vivienda",
        "B22": "B12. Gastos médicos y cuidado personal",
        "B23": "B13. Deportes",
        "B24": "B14. Formación",
        # [B20] Gastos de dieta
        "B31": "B21. Comida y bebida",
        "B33": "B22. Antojos",
        "B34": "B23. Alcohol y drogas",
        "B35": "B24. Restaurantes y bares",
        # [B30] Gastos de consumo
        "B41": "B31. Compras y servicios generales",
        "B43": "B32. Limpieza e higiene",
        "B44": "B33. Herramientas y tecnología",
        "B45": "B34. Ropa y accesorios",
        "B81": "B35. Regalos",
        "B82": "B36. Donaciones",
        "B83": "B37. Loterías y apuestas",
        # [B40] Gasto de transporte
        "B51": "B41. Coche, gasolina y peajes",
        "B52": "B42. VTC",
        "B53": "B43. Transporte público",
        "B54": "B44. Viajes",
        # [B50] Gastos de entretenimiento
        "B61": "B51. Entretenimiento general",
        "B62": "B52. Literatura",
        "B63": "B53. Cine y teatro",
        "B64": "B54. Videojuegos",
        "B75": "B55. TV y streaming",
        "B71": "B56. Eventos y ocio local",
        "B72": "B57. Discotecas y locales",
        "B73": "B58. Conciertos y festivales",
        "B74": "B59. Vacaciones",
    }
    old_code_to_category = {}
    for old_code in renaming:
        old_code_to_category[old_code] = cats.subset(code=old_code)
    for old_code, new_name in renaming.items():
        print(f"{old_code} --> {new_name}")
        old_code_to_category[old_code].name = new_name
    print()
    cats.subset(lambda x: x.code.startswith("B")).sort().show()


if __name__ == "__main__":
    m = Marx()
    m.load(TARGET_FILE)

    if 1:
        do_income(m)
        do_expenses(m)

    res = m.save()
    print("Guardado en", res)
