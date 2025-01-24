# Creado: 13/12/2024
"""Wrapped de Contabilidad"""

import os
import sys
from datetime import datetime

import openpyxl

from marx import Marx
from marx.models import MarxDataStruct

MARX_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__) + "/marx"))
sys.path.append(os.path.dirname(MARX_DIR))

MARX_DATA_FILE = r"G:\Mi unidad\MiBilletera Backups\Dic_01_2024_ExpensoDB"

WRAPPED_FILEPATH = r"C:\Users\angel\Playground\wrapped.xlsx"
FROM_DATE = datetime(2024, 1, 1)
TO_DATE = datetime(2025, 1, 1)


# Funciones auxiliares


def simplify_text(text: str) -> str:
    """Simplifica el texto para comparaciones"""
    text = text.lower()
    text = text.replace("\n", " | ")
    text = text.replace("á", "a")
    text = text.replace("é", "e")
    text = text.replace("í", "i")
    text = text.replace("ó", "o")
    text = text.replace("ú", "u")
    return text


# Funciones principales


def wrap(
    data: MarxDataStruct,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
) -> list[tuple[int, str, str, str, str, float, float]]:
    """Genera un juego de datos organizando anualmente

    De entrada, se puede especificar un rango de fechas para filtrar los datos.
    En caso de no especificar ninguna fecha, se toman todos los datos.

    Las variables generadas son:
    - 'year': Año de la entrada
    - 'account': Cuenta de la entrada
    - 'flow': Dirección del flujo de dinero, entre 'profit', 'loss',
    'transfer.inbound' y 'transfer.outbound'
    - 'category': Categoría de la entrada
    - 'concept': Concepto de la entrada
    - 'amount': Monto neto de la entrada
    - 'rel_amount': Monto relativo de la entrada respecto al total generado por
    ('year', 'flow')

    Devuelve una lista de tuplas con las variables generadas.

    """
    from_date = from_date or datetime(1, 1, 1)
    to_date = to_date or datetime(9999, 12, 31)

    # Agrupar
    grouped = {}
    for event in data.events.subset(
        lambda x: ((to_date > x.date >= from_date) & (x.status == 1))
    ):
        # Base de la clave
        key = [
            event.date.year,
            None,
            None,
            event.category.name,
            simplify_text(event.concept),
        ]
        # Flujo
        flow = event.flow
        if flow == event.TRANSFER:
            key[1] = event.orig.name
            key[2] = "transfer.outbound"
            grouped[tuple(key)] = grouped.get(tuple(key), 0) + event.amount
            key[1] = event.dest.name
            key[2] = "transfer.inbound"
            grouped[tuple(key)] = grouped.get(tuple(key), 0) + event.amount
        elif flow == event.INCOME:
            key[1] = event.dest.name
            key[2] = "profit"
            grouped[tuple(key)] = grouped.get(tuple(key), 0) + event.amount
        elif flow == event.EXPENSE:
            key[1] = event.orig.name
            key[2] = "loss"
            grouped[tuple(key)] = grouped.get(tuple(key), 0) + event.amount

    # Calcular totales
    totals = {}
    for key, amount in grouped.items():
        year, account, flow, *_ = key
        totals[(year, account, flow)] = totals.get((year, account, flow), 0) + amount

    # Generar datos
    wrapped = []
    for key, amount in grouped.items():
        year, account, flow, category, concept = key
        total = totals[(year, account, flow)]
        wrapped.append((year, account, flow, category, concept, amount, amount / total))

    return wrapped


def create_datasheet(
    filepath: str, table: list[tuple[int, str, str, str, str, float, float]]
) -> str:
    """Crea una hoja de cálculo con los datos generados"""
    wb = openpyxl.Workbook()

    # Hoja de datos principales
    main_sheet = wb[wb.sheetnames[0]]
    main_sheet.title = "Wrapped"
    main_sheet.append(
        ["Año", "Cuenta", "Flujo", "Categoría", "Concepto", "Monto", "Monto relativo"]
    )
    for row in table:
        main_sheet.append(row)

    # Guardar
    wb.save(filepath)
    wb.close()
    return filepath


if __name__ == "__main__":
    marx = Marx()
    marx.load(MARX_DATA_FILE)

    wrapped = wrap(marx.data)
    path = create_datasheet(WRAPPED_FILEPATH, wrapped)

    print(f"Datos generados y guardados en '{path}'")
