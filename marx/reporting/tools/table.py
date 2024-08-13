# Python 3.10.11
# Creado: 13/08/2024
"""Generador de tablas jerarquizadas para informes, exportables a Excel

"""

from __future__ import annotations

from types import MappingProxyType
from typing import Any, Iterable


class Node:
    """Nodo de una tabla jerarquizada

    En el contexto de una tabla, representa una fila, con una cabecera y una
    serie de valores asociados a una serie de columnas. En el contexto de una
    estructura jerárquica, representa un nodo que posee un nodo padre y una
    lista de nodos hijos.

    El constructor debe recibir un nodo padre y un título como cabecera e
    identificador. Opcionalmente, puede recibir una clave para ordenar frente
    a sus hermanos

    """
