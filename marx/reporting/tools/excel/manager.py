# Python 3.10.11
# Creado: 13/08/2024
"""Interfaz para gestión de hojas de cálculo de Excel

Usa OpenPyXL como base, pero utiliza nuevos mecanismos para que el manejo sea
más similar a la propia API de Excel.

"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import openpyxl
from openpyxl.cell.cell import Cell as _OpenPyXLCell
from openpyxl.worksheet.worksheet import Worksheet as _OpenPyXLSheet
from sniffio import current_async_library

OpenPyXLCell = _OpenPyXLCell
OpenPyXLSheet = _OpenPyXLSheet

CellID = str | tuple[str | int, int]


@dataclass
class CellManager:
    """Celda de una hoja de cálculo de Excel"""

    _base: OpenPyXLCell

    @property
    def cell(self) -> OpenPyXLCell:
        return self._base

    @property
    def value(self) -> Any:
        return self._base.value

    @value.setter
    def value(self, value: Any) -> None:
        self._base.value = value

    @property
    def row(self) -> int:
        return self._base.row

    @property
    def column(self) -> int:
        return self._base.column

    @property
    def lcolumn(self) -> str:
        return self._base.column_letter

    @property
    def address(self) -> str:
        return self._base.coordinate

    def __str__(self) -> str:
        return f"CellManager({self.address!r})"


@dataclass
class SheetManager:
    """Hoja de cálculo de Excel"""

    _base: OpenPyXLSheet

    def __post_init__(self) -> None:
        self._cells = {}

        # configuración por defecto
        self._base.sheet_properties.outlinePr.summaryBelow = False

    @property
    def name(self) -> str:
        """Título de la hoja de cálculo"""
        return self._base.title

    @name.setter
    def name(self, value: str) -> None:
        self._base.title = value

    # métodos generales

    def clear(self) -> SheetManager:
        """Borra el contenido de la hoja de cálculo"""
        self._base.delete_rows(1, self._base.max_row)
        return self

    # configuración de página

    def set_column_width(self, column: str | int, width: int) -> SheetManager:
        """Establece el ancho de una columna

        La columna puede indicarse mediante su índice (empezando por 1) o
        mediante su letra.

        """
        if isinstance(column, int):
            column = chr(column + 64)
        self._base.column_dimensions[column.upper()].width = width

    # selección de celdas

    def point(
        self, cell_id: CellID | None = None, *, row: int | None = None, column: int | None = None
    ) -> CellPointer:
        """Crea un puntero a una celda de la hoja de cálculo

        Se puede indicar la celda mediante un identificador de celdas (nombre
        o coordenadas en forma de tupla) o indicando directamente el índice
        numérico de la fila y la columna.

        """
        if cell_id is None:
            if row is None or column is None:
                raise ValueError(
                    "[ExcelManager] Se debe indicar una celda o una fila y una columna"
                )
            cell_id = (row, column)
        if isinstance(cell_id, tuple):
            col, row = cell_id
            if isinstance(col, int):
                col = chr(col + 64)
            cell_id = f"{col}{row}"
        if isinstance(cell_id, str):
            cell = self._base[cell_id]
            return CellPointer(self, cell)

    # representación

    def __str__(self) -> str:
        return f"ExcelSheetManager({self.name!r})"


class CellPointer:
    """Puntero a una celda de una hoja de cálculo de Excel"""

    def __init__(self, sheet: SheetManager, cell: OpenPyXLCell):
        self.sheet = sheet
        self.cell = CellManager(cell)

    @property
    def current(self) -> str:
        return self.cell.address

    def goto(
        self, cell_id: CellID | None = None, *, row: int | None = None, column: int | None = None
    ) -> CellPointer:
        """Se mueve a una celda de la hoja de cálculo

        Se puede indicar la celda mediante un identificador de celdas (nombre
        o coordenadas en forma de tupla) o indicando directamente el índice
        numérico de la fila y la columna.

        """
        return self.sheet.point(cell_id=cell_id, row=row, column=column)

    def right(self, steps: int = 1) -> CellPointer:
        """Se mueve a la derecha una cantidad de pasos"""
        return self.goto(column=self.cell.column + steps)
