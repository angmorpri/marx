# Python 3.10.11
# Creado: 17/08/2024
"""Parser de fórmulas de Excel"""

import re
from typing import Iterable

# from marx.reporting.tools import TreeNode


NODE_REFERENCE_PATTERN = r"\{(.*?)\}"
KEY_CHILDREN = "@CHILDREN"
KEY_SIBLINGS = "@SIBLINGS"


def address_grouper(nodes: Iterable["TreeNode"], column: str) -> str:
    """Trata de agrupar las direcciones de los nodos en bloques contiguos

    Devuelve una cadena de texto con las direcciones de los nodos agrupadas,
    separando bloques iguales con ':', y bloques diferentes con ','; como se
    espera en una fórmula de Excel.

    """
    block = []
    blocks = []
    prev_row = -1
    for current_row in (node.row for node in nodes if hasattr(node, "row")):
        address = f"{column}{current_row}"
        if current_row == (prev_row + 1):
            block.append(address)
        else:
            if block:
                blocks.append(":".join(block))
            block = [address]
        prev_row = current_row
    if block:
        blocks.append(":".join(block))
    return ",".join(blocks)


def parse_formula(formula: str, node: "TreeNode", target_column: str) -> str:
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
        addresses = address_grouper(node.children, target_column)
        formula = formula.replace(KEY_CHILDREN, addresses)
    if KEY_SIBLINGS in formula:
        addresses = address_grouper(node.siblings, target_column)
        formula = formula.replace(KEY_SIBLINGS, addresses)
    return formula
