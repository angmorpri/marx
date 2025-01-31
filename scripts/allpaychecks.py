# 2025/01/31
"""Listado de todas las nóminas"""

from datetime import datetime
from pathlib import Path

import openpyxl

from marx import Marx
from marx.automation import PaycheckParser
from marx.models import MarxDataStruct

DATABASE_PATH = Path(__file__).parent / "MOD_Ene_29_2025_ExpensoDB"
CRITERIA_PATH = Path(r"C:\Users\angel\Config\marx\criteria\paycheck.toml")
OUTPUT_PATH = Path(__file__).parent / "paychecks.xlsx"

PAYCHECKS_DIR = Path(r"C:\Users\angel\OneDrive - Telefonica\Documentos\Nóminas")


def main(data: MarxDataStruct):
    """Listado de todas las nóminas"""
    parser = PaycheckParser(data, CRITERIA_PATH)
    wb = openpyxl.Workbook()
    for year in (2022, 2023, 2024):
        path = PAYCHECKS_DIR / str(year)
        wb.create_sheet(str(year))
        sheet = wb[str(year)]
        sheet.append(
            [
                "Fecha",
                "Nómina bruta",
                "Paga extra",
                "IRPF",
                "IRPF teórico (%)",
                "Seguridad Social",
            ]
        )
        for paycheck_file in path.glob("*.pdf"):
            month = int(paycheck_file.stem.split("-")[0])
            date = datetime(year, month, 1)
            row = [date.strftime("%Y-%m-%d"), 0.0, 0.0, 0.0, None, 0.0]
            for event in parser.parse(paycheck_file, date):
                if event.concept == "Nómina bruta":
                    row[1] = event.amount
                elif "extra" in event.concept.lower():
                    row[2] = event.amount
                elif event.concept == "IRPF":
                    row[3] = event.amount
                    row[4] = event.details.strip("(").strip(")")
                elif event.concept == "Seguridad Social":
                    row[5] = event.amount
            print(">>>", row)
            sheet.append(row)

    wb.save(OUTPUT_PATH)
    wb.close()


if __name__ == "__main__":
    marx = Marx()
    marx.load(DATABASE_PATH)
    main(marx.data)
    print("DONE")
