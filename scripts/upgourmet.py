# Python 3.10.11
# Creado: 31/01/2024
"""Creación de la cuenta UpGourmet."""
import os
import sys

MARX_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__) + "/marx"))
sys.path.append(os.path.dirname(MARX_DIR))


import time
from datetime import datetime
from pathlib import Path

import openpyxl

from marx.model import MarxMapper
from marx.util import get_most_recent_db


COUNTERPART_TRANSLATION = {
    "PENJAMO": 'Restaurante "Penjamo"',
    "TELEPIZZA KANSAS CITY": "Telepizza",
    "LA MUSA DE ESPRONCEDA": "La Musa de Espronceda",
    "WWW.JUST-EAT.ES": "JustEat",
    "JustEat": "JustEat",
    "CONXURO": 'Bar "Conxuro"',
    "SANISSIMO": 'Bar "Sanissimo"',
    "EL CASINILLO II": 'Restaurante "El Casinillo II"',
    "TABANCO LA DUQUESA": 'Tabanco "La Duquesa"',
    "BAR MENTRIDA": 'Bar "Mentrida"',
    "SIST INDUSTRIALES HERICE": "Desconocido",
    "": "Telefónica",
}


class UpGourmet:
    def __init__(self, adapter: MarxMapper, path: str | Path) -> None:
        self.adapter = adapter
        self.path = path
        self.data = []
        self.load_excel()

    def load_excel(self) -> None:
        """Carga el Excel con los datos de UpGourmet."""
        wb = openpyxl.load_workbook(self.path)
        sheet = wb.active
        for date, *_, ex, pr, cp, _ in sheet.iter_rows(min_row=2, values_only=True):
            date = datetime.strptime(date, "%d/%m/%Y")
            amount = +float(pr) if pr else -float(ex)
            cp = COUNTERPART_TRANSLATION.get(cp.strip().split("   ")[0])
            row = {"date": date, "amount": amount, "cp": cp}
            self.data.append(row)
        wb.close()

    def get_different_counterparts(self) -> list[str]:
        """Devuelve las contrapartidas diferentes."""
        res = set()
        for row in self.data:
            cp = row["cp"].strip().split("   ")[0]
            res.add(cp)
        return list(res)

    # Creación para Marx

    def create_account(self) -> None:
        """Crea la cuenta UpGourmet para Marx.

        Añade todos los registros necesarios.

        """
        suite = self.adapter.load()
        # Cuenta
        upgourmet = suite.accounts.new(-1, "UpGourmet", 100, "#F59100").entity
        # Registros
        for row in self.data:
            date = row["date"]
            amount = round(row["amount"], 2)
            if amount > 0:
                orig = row["cp"]
                dest = upgourmet
            else:
                orig = upgourmet
                dest = row["cp"]
                amount = -amount
            # Categoría
            if row["cp"] == "Telefónica":
                category = suite.categories.get("A11").entity
                concept = "Dieta mensual"
            elif row["cp"] == "JustEat":
                category = suite.categories.get("B63").entity
                concept = "Porquerías"
            else:
                category = suite.categories.get("B61").entity
                concept = "Comida"
            event = suite.events.new(-1, date, amount, category, orig, dest, concept)
            print(event)


if __name__ == "__main__":
    # source = Path("G:/Mi unidad/MiBilletera Backups/MOD_Ene_31_2024_ExpensoDB.db")
    source = get_most_recent_db("G:/Mi unidad/MiBilletera Backups")
    print(">>> Usando: ", source)
    time.sleep(1)

    adapter = MarxMapper(source)

    ug = UpGourmet(adapter, "C:/Users/angel/Desktop/marx/UpGourmet.xlsx")
    ug.create_account()
    adapter.save()
    time.sleep(1)
    input()

    for event in adapter.data.events.sort("date"):
        print(event)
