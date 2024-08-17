# Python 3.10.11
# Creado: 05/03/2024
"""Herramientas y utilidades para manejar hojas de cálculo de Excel."""

from .formula import parse_formula
from .manager import CellID, CellManager, SheetManager, CellPointer, OpenPyXLCell, OpenPyXLSheet
