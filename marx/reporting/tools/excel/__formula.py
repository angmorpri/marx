# 3.10.11
# Creado: 12/03/2024
"""Módulo para generar fórmulas de Excel de forma dinámica."""

from typing import Iterable

from marx.reporting.excel import CellID


class Formula:
    """Fórmula de Excel.

    Cada fórmula se compone de unos componentes ordenados ('components'), que
    pueden ser celdas, valores, operaciones o funciones de Excel. Al convertir
    un objeto fórmula a texto, se generará una cadena tal que represente de
    forma adecuada la fórmula de Excel que representa.

    El constructor recibe una cantidad arbitraria de componentes en el orden
    adecuado. Cada componente puede ser:
        - Un valor numérico.
        - Un identificador o una lista de identificadores de celda.
        - El nombre de una función válida de Excel.
        - Operadores estándar.

    """

    def __init__(self, *components: int | float | str | CellID | Iterable[CellID]):
        self.components = components

    def build(self) -> str:
        """Construye la fórmula de Excel."""
        formula = []
        for component in self.components:
            if isinstance(component, (list, tuple)):
                component = self._group_cells(component)
            formula.append(str(component))
        if formula[0] in ("SUM",):
            formula.insert(1, "(")
            formula.append(")")
        return "=" + "".join(formula)

    def _group_cells(self, cells: Iterable[CellID]) -> str:
        """Agrupa celdas en una fórmula."""
        cells = list(sorted(cells))
        cell_ranges = []
        prev_cell = None
        for cell in cells:
            if prev_cell is None:
                prev_cell = cell
                cell_ranges.append([cell, None])
                continue
            if abs(cell.col - prev_cell.col) == 1 and cell.row == prev_cell.row:
                cell_ranges[-1][1] = cell
            elif abs(cell.row - prev_cell.row) == 1 and cell.col == prev_cell.col:
                cell_ranges[-1][1] = cell
            else:
                cell_ranges.append([cell, None])
            prev_cell = cell
        formatted = []
        for start, end in cell_ranges:
            if end is None:
                formatted.append(start.id)
            else:
                formatted.append(f"{start.id}:{end.id}")
        return ",".join(formatted)

    def __str__(self) -> str:
        return self.build()
