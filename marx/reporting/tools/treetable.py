# Python 3.10.11
# Creado: 13/08/2024
"""Generador de tablas jerarquizadas para informes, exportables a Excel

Presenta la clase 'TreeTable', que gestiona una serie de nodos 'TreeNode', cada
uno con una serie de parámetros que lo configuran como fila de una tabla y
como nodo de una estructura jerárquica.

"""

from __future__ import annotations

from dataclasses import dataclass
from types import EllipsisType
from typing import Any, Iterable

ColID = str
RowID = str


class RowValuesDict(dict):
    """Diccionario para asignar valores a las columnas de una fila de una tabla

    Se comporta como un diccionario normal, pero sólo admite claves que sean
    identificadores de columnas de la tabla. Por defecto, los valores serán
    0.

    Se puede usar la clave especial ... (Ellipsis), para modificar el valor de
    todas las columnas de la tabla a la vez.

    """

    def __init__(self, keys: Iterable[str]) -> None:
        self._keys = keys
        super().__init__({key: 0 for key in self._keys})

    def __getitme__(self, key: str | EllipsisType) -> Any:
        if key is Ellipsis:
            return list(self.values())
        elif key not in self._keys:
            raise KeyError(f"[TreeTable] La columna identificada por '{key}' no existe")
        return super().__getitem__(key)

    def __setitem__(self, key: str | EllipsisType, value: Any) -> None:
        if key is Ellipsis:
            for key in self._keys:
                super().__setitem__(key, value)
        elif key not in self._keys:
            raise KeyError(f"[TreeTable] La columna identificada por '{key}' no existe")
        super().__setitem__(key, value)


@dataclass
class TreeNode:
    """Nodo de una tabla jerarquizada

    En el contexto de una tabla, representa una fila, con una cabecera y una
    serie de valores asociados a una serie de columnas. En el contexto de una
    estructura jerárquica, representa un nodo que posee un nodo padre y una
    lista de nodos hijos.

    Los nodos de una tabla jerárquica no deben ser instanciados directamente,
    sino a través del método 'append' de un nodo padre o de la tabla matriz.

    """

    parent: TreeNode | None
    id: str
    title: str
    omit_if_childless: bool
    sort_with: Any

    def __post_init__(self) -> None:
        self._children = []
        self.values = RowValuesDict(self.master.headers)

    @property
    def master(self) -> TreeTable:
        return self.parent.master

    @property
    def children(self) -> Iterable[TreeNode]:
        yield from sorted(self._children, key=lambda node: node.sort_with)

    @property
    def siblings(self) -> Iterable[TreeNode]:
        yield from [node for node in self.parent._children if node is not self]

    @property
    def level(self) -> int:
        return 0 if self.parent is None else self.parent.level + 1

    def has_children(self) -> bool:
        return bool(self._children)

    # métodos de jerarquía

    def append(
        self, id: str, title: str, *, omit_if_childless: bool = False, sort_with: Any = None
    ) -> TreeNode:
        """Crea un nuevo nodo hijo y lo devuelve

        Si ya existe un nodo hijo con el mismo identificador, no se creará uno
        nuevo y se devolverá el ya existente sin modificar sus atributos. Si
        ya existe un nodo con el mismo identificador en otro punto del árbol,
        se lanzará una excepción.

        """
        # comprobar si ya existe un nodo con el mismo identificador
        if id in [node.id for node in self._children]:
            return self.master[id]
        elif id in [node.id for node in self.master.iter_all()]:
            raise ValueError(f"[TreeTable] Ya existe un nodo con el identificador '{id}'")
        # crear el nuevo nodo
        sort_with = sort_with or (len(self._children) + 1)
        child = TreeNode(self, id, title, omit_if_childless, sort_with)
        self._children.append(child)
        self.master._nodes[id] = child
        return child

    def __iter__(self) -> Iterable[TreeNode]:
        """Itera sobre los nodos hijos de este nodo"""
        yield from self.children

    def iter_all(self) -> Iterable[TreeNode]:
        """Itera sobre todos los nodos a partir de este nodo"""
        yield self
        for child in self.children:
            yield from child.iter_all()

    # métodos de representación

    def __str__(self) -> str:
        return f"Node({self.id}, {self.title})"


class TreeTable(TreeNode):
    """Tabla jerárquica

    Una tabla jerárquica es una estructura de datos que representa una tabla
    en la que las filas pueden estar anidadas unas dentro de otras. Cada fila
    se representa mediante un objeto 'TreeNode', que posee un título de
    cabecera y una serie de valores asociados a las columnas de la tabla,
    identificadas por un ID único.

    El constructor recibe el título de la tabla y, opcionalmente, la lista de
    identificadores de las columnas. Si no se especifican, se deberá añadir
    posteriormente mediante el método 'set_headers'.

    """

    def __init__(self, title: str, headers: Iterable[str] | None = None) -> None:
        self.headers = headers or []
        self._nodes = {}
        super().__init__(None, "", title, False, None)

    @property
    def master(self) -> TreeTable:
        return self

    def set_headers(self, headers: Iterable[str]) -> None:
        """Establece las cabeceras de la tabla"""
        self.headers = list(headers)

    def __getitem__(self, id: str) -> TreeNode:
        return self._nodes[id]

    def __str__(self) -> str:
        return f"TreeTable({self.title}, {len(self._nodes)} nodes, {len(self.headers)} columns)"
