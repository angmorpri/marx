# Python 3.10.11
# Creado: 13/08/2024
"""Interfaz para gestión de hojas de cálculo de Excel

Usa OpenPyXL como base, pero utiliza nuevos mecanismos para que el manejo sea
más similar a la propia API de Excel.

"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypedDict

from openpyxl.cell.cell import Cell as _OpenPyXLCell
from openpyxl.worksheet.worksheet import Worksheet as _OpenPyXLSheet

OpenPyXLCell = _OpenPyXLCell
OpenPyXLSheet = _OpenPyXLSheet

CellIDArgs = str | tuple[str | int, int]


class CellIDKwargs(TypedDict):
    column: str | int | None
    row: int | None


class CellID:
    """Identificador de celdas de una hoja de cálculo de Excel

    Normaliza la forma de identificar una celda, ya que permite indicarla
    mediante su dirección ('address'), con formato "<col_letter><row>";
    mediante una tupla (<col>, <row>), donde "<col>" puede ser un número o una
    letra; o, finalmente, indicando columna y fila por separado usando las
    palabras claves 'column' y 'row'.

    """

    def __init__(
        self,
        value: str | tuple[str | int, int] | None = None,
        *,
        column: str | int | None = None,
        row: int | None = None,
    ):
        self._col = None
        self._row = None
        # comprobaciones
        if value is None and (column is None or row is None):
            raise ValueError("[ExcelManager] No se ha indicado un identificador de celda válido")
        # mediante argumentos
        if isinstance(value, str):
            value = ("".join(filter(str.isalpha, value)), int("".join(filter(str.isdigit, value))))
        if isinstance(value, tuple):
            col, self._row = value
            if isinstance(col, str):
                col = ord(col.upper()) - 64
            self._col = col
        # mediante palabras clave
        if column is not None:
            if isinstance(column, str):
                column = ord(column.upper()) - 64
            self._col = column
        if row is not None:
            self._row = row

    @property
    def column(self) -> int:
        return self._col

    @property
    def lcolumn(self) -> str:
        return chr(self._col + 64)

    @property
    def row(self) -> int:
        return self._row

    @property
    def coords(self) -> tuple[int, int]:
        return self._col, self._row

    @property
    def address(self) -> str:
        return f"{self.lcolumn}{self._row}"

    def __hash__(self) -> int:
        return hash((self._col, self._row))

    def __str__(self) -> str:
        return f"CellID({self.column!r}, {self.row!r})"


@dataclass
class CellManager:
    """Celda de una hoja de cálculo de Excel"""

    id: CellID
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
    def column(self) -> int:
        return self.id.column

    @property
    def lcolumn(self) -> str:
        return self.id.lcolumn

    @property
    def row(self) -> int:
        return self.id.row

    @property
    def address(self) -> str:
        return self.id.address

    def stylize(self) -> CellManager:
        raise NotImplementedError

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

    def get(self, *args: CellIDArgs, **kwargs: CellIDKwargs) -> CellManager:
        cell_id = CellID(*args, **kwargs)
        if cell_id not in self._cells:
            self._cells[cell_id] = CellManager(cell_id, self._base[cell_id.address])
        return self._cells[cell_id]

    def __getitem__(self, *args: CellIDArgs) -> CellManager:
        """Sugar syntax para obtener una celda de la hoja de cálculo"""
        return self.get(*args)

    def point(self, *args: CellIDArgs, **kwargs: CellIDKwargs) -> CellPointer:
        """Crea un puntero a una celda de la hoja de cálculo

        Se puede indicar la celda mediante un identificador de celdas (nombre
        o coordenadas en forma de tupla) o indicando directamente el índice
        numérico de la fila y la columna.

        """
        return CellPointer(self, self.get(*args, **kwargs))

    # representación

    def __str__(self) -> str:
        return f"SheetManager({self.name!r})"


class CellPointer:
    """Puntero a una celda de una hoja de cálculo de Excel"""

    def __init__(self, sheet: SheetManager, cell: CellManager) -> None:
        self.sheet = sheet
        self.cell = cell

    @property
    def current(self) -> str:
        return self.cell.address

    # métodos de navegación

    def goto(self, *args: CellIDArgs, **kwargs: CellIDKwargs) -> CellPointer:
        """Se mueve a una celda de la hoja de cálculo"""
        self.cell = self.sheet.get(*args, **kwargs)
        return self

    def right(self, steps: int = 1) -> CellPointer:
        """Se mueve a la derecha una cantidad de pasos"""
        return self.goto(column=self.cell.column + steps, row=self.cell.row)

    def down(self, steps: int = 1) -> CellPointer:
        """Se mueve hacia abajo una cantidad de pasos"""
        return self.goto(column=self.cell.column, row=self.cell.row + steps)

    def left(self, steps: int = 1) -> CellPointer:
        """Se mueve a la izquierda una cantidad de pasos"""
        return self.goto(column=self.cell.column - steps, row=self.cell.row)

    def up(self, steps: int = 1) -> CellPointer:
        """Se mueve hacia arriba una cantidad de pasos"""
        return self.goto(column=self.cell.column, row=self.cell.row - steps)

    def ln(self, steps: int = 1) -> CellPointer:
        """Salta a la siguiente fila"""
        return self.goto(column=1, row=self.cell.row + steps)
