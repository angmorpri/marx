# Python 3.10.11
# Creado: 17/08/2024
"""Parser de fórmulas de Excel"""
from __future__ import annotations

import re
from typing import Iterable, TYPE_CHECKING

if TYPE_CHECKING:
    from marx.reporting.tools import TreeNode


NODE_REFERENCE_PATTERN = r"\{(.*?)\}"
KEY_CHILDREN = "@CHILDREN"
KEY_SIBLINGS = "@SIBLINGS"


def address_grouper(nodes: Iterable[TreeNode], column: str) -> str:
    """Trata de agrupar las direcciones de los nodos en bloques contiguos

    Devuelve una cadena de texto con las direcciones de los nodos agrupadas,
    separando bloques iguales con ':', y bloques diferentes con ','; como se
    espera en una fórmula de Excel.

    """
    b_start, b_end = None, None
    blocks = []
    prev_row = -1
    for current_row in (node.row for node in nodes if node.row != -1):
        if current_row == (prev_row + 1):
            b_end = f"{column}{current_row}"
        else:
            if b_start and b_end:
                blocks.append(f"{b_start}:{b_end}")
            elif b_start:
                blocks.append(b_start)
            b_start = f"{column}{current_row}"
        prev_row = current_row
    if b_start and b_end:
        blocks.append(f"{b_start}:{b_end}")
    elif b_start:
        blocks.append(b_start)
    return ",".join(blocks)


def parse_formula(formula: str, node: TreeNode, target_column: str) -> str:
    """Procesa una fórmula, convirtiéndola en un formato válido para Excel

    Una fórmula es una cadena de texto que comienza con '=', y contiene
    operaciones y funciones válidas de Excel. Además, admite referencias a
    nodos de una tabla jerárquica, indicados por su ID entre llaves ({}).
    También admite algunas claves especiales, precedidas por '@', como
    '@CHILDREN' para referirse a todos los hijos de un nodo, o '@SIBLINGS' para
    referirse a todos los hermanos del nodo.

    'target_column' debe ser la letra de la columna de Excel en la que se
    escribirá el resultado de la fórmula.

    Devuelve la fórmula lista para ser usada en una hoja de cálculo de Excel.

    """
    # comprobaciones
    if not formula.startswith("="):
        raise ValueError("[ExcelFormula] La fórmula debe comenzar con '='")
    # referencias a nodos
    for match in re.findall(NODE_REFERENCE_PATTERN, formula):
        if not match in node.master:
            raise ValueError(
                f"[ExcelFormula] No se encuentra el nodo con ID '{match}' para la fórmula '{formula}'"
            )
        ref = f"{target_column}{node.master[match].row}"
        formula = formula.replace("{" + match + "}", ref)
    # claves especiales
    if KEY_CHILDREN in formula:
        children = [node for node in node.children if node.row != -1]
        if not children:
            return "=0"
        addresses = address_grouper(children, target_column)
        formula = formula.replace(KEY_CHILDREN, addresses)
    if KEY_SIBLINGS in formula:
        siblings = [node for node in node.siblings if node.row != -1]
        if not siblings:
            return "=0"
        addresses = address_grouper(siblings, target_column)
        formula = formula.replace(KEY_SIBLINGS, addresses)
    return formula.replace(" ", "")
