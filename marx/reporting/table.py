# Python 3.10.11
# Creado: 28/02/2024
"""Módulo que define la clase "TableBuilder", que permite crear tablas
jerárquicas de datos que luego pueden ser exportadas a distintos formatos.

La clase principal es TableBuilder, que se compone de diferentes TableNode que
representan las filas de la tabla.

"""
from __future__ import annotations

import random
from types import MappingProxyType
from typing import Any, Iterable, Literal


class TableNode:
    """Clase que representa un nodo de una tabla de datos.

    Un nodo es una fila de la tabla que también se comporta como un nodo dentro
    de una estructura de árbol, permitiendo generar una tabla jerarquizada.

    Como parte de un nodo de árbol, se compone de un TableBuilder maestro
    ('master'), de un padre ('parent') y de una lista de hijos ('children').
    Como fila, contiene un título ('title') y una lista de valores ('values').
    En función del tipo de fila, los valores pueden ser directamente datos, o
    agregaciones de datos de otras filas. Las opciones son:
        - "VALUE": los valores son datos directos.
        - "SUM_CHILDREN": los valores son la suma de los valores de sus nodos
            hijos.
        - "SUM_SIBLINGS": los valores son la suma de los valores de sus nodos
            hermanos.

    Además, cada nodo tiene un identificador único ('id'), que no puede
    repetirse dentro de un mismo TableBuilder. También se dispone de una llave
    'order' para determinar el orden en el que tienen que aparecer los hijos
    cuando sean representados.

    El constructor recibe los siguientes parámetros:
        - parent: el nodo padre de la fila. Debe definir 'master'. Obligatorio.
        - title: el título de la fila. Obligatorio.
        - id: el identificador único de la fila. Si no se proporciona, se
            utilizará 'title'.
        - values: indica el tipo de valor que gestionará la fila. Debe ser
            "VALUE", "SUM_CHILDREN" o "SUM_SIBLINGS". Por defecto, será
            "VALUE".
        - order: el orden en el que aparecerá la fila. Si no se indica, se
            utilizará el orden de creación.

    """

    GLOBAL_INDEX = 100

    def __init__(
        self,
        parent: TableNode | TableBuilder,
        title: str,
        id: str | None = None,
        *,
        values: Literal["VALUE", "SUM_CHILDREN", "SUM_SIBLINGS"] = "VALUE",
        order: Any = None,
    ):
        # Nodo
        if not parent.master:
            raise ValueError("El nodo padre debe definir un TableBuilder maestro.")
        self.parent = parent
        self.master = parent.master
        self.children = []

        # Fila
        self.title = title
        self.id = id or title
        self.values_type = values
        self._values = {key: 0.0 for key in self.master.headers}
        if not order:
            self.order = TableNode.GLOBAL_INDEX
            TableNode.GLOBAL_INDEX += 1
        else:
            self.order = order

    @property
    def siblings(self) -> Iterable[TableNode]:
        """Devuelve la lista de nodos hermanos del nodo actual, SIN contar el
        nodo actual.

        """
        return [child for child in self.parent.children if child != self]

    @property
    def generation(self) -> int:
        """Devuelve la generación del nodo en la jerarquía de la tabla.

        La generación de un nodo raíz es 0, y la de sus hijos es 1, y así
        sucesivamente.

        """
        generation = 0
        parent = self.parent
        while parent:
            generation += 1
            parent = parent.parent
        return generation

    @property
    def values(self) -> dict[str, float] | MappingProxyType[str, float]:
        """Devuelve los valores de la fila, en función del tipo de valores que
        gestiona.

        En caso de no gestionar valores directamente, se devolverá una vista
        del diccionario, para que no se puedan modificar sus valores.

        """
        if self.values_type == "VALUE":
            return self._values
        elif self.values_type == "SUM_CHILDREN":
            for key in self._values:
                self._values[key] = sum(child._values[key] for child in self.children)
        elif self.values_type == "SUM_SIBLINGS":
            for key in self._values:
                self._values[key] = sum(sibling._values[key] for sibling in self.siblings)
        return MappingProxyType(self._values)

    def has_children(self) -> bool:
        """Indica si el nodo tiene hijos o no."""
        return bool(self.children)

    def has_grandchildren(self) -> bool:
        """Indica si el nodo tiene nietos o no."""
        return any(child.has_children() for child in self.children)

    def append(
        self, title: str, id: str | None = None, *, values: str = "VALUE", order: Any = None
    ) -> TableNode:
        """Añade un nodo hijo a la fila actual.

        También se añade al diccionario global de nodos del TableBuilder
        maestro.

        Si se trata de añadir un nodo cuyo ID ya exista, no creará ni añadirá
        un nuevo nodo y devolverá el ya existente.

        """
        id = id or title
        if id in self.master.nodes:
            return self.master.nodes[id]

        child = TableNode(self, title, id, values=values, order=order)
        self.children.append(child)
        self.master.nodes[id] = child
        return child

    def __getitem__(self, id: str) -> TableNode:
        """Devuelve un nodo con el ID indicado que esté subordinado a éste.

        Si no lo encuentra, lanzará un KeyError.

        """
        for child in self.children:
            if child.id == id:
                return child
            elif child.has_children():
                return child[id]
        raise KeyError(
            f"No se ha encontrado ningún nodo con el ID '{id}'." f" desde el nodo '{self.id}'"
        )

    def __iter__(self) -> Iterable[TableNode]:
        """Devuelve un iterador sobre los nodos hijos de la fila, ordenados."""
        return iter(sorted(self.children, key=lambda node: node.order))

    def __str__(self) -> str:
        return f"[{self.id:*>10}]{'  '*self.generation}{self.title} | {self.values}"


class TableBuilder:
    """Clase que gestiona la creación de una tabla de datos jerárquica.

    Esta clase actúa como un concentrador de los nodos de la tabla. A su vez,
    define los encabezados de las columnas.

    Se proporciona el método 'append' para añadir nodos a la tabla. También se
    puede acceder a los nodos directamente en modo lista (table[...]) usando el
    ID de cualquier nodo.

    El constructor recibe un iterable con los títulos de las cabeceras de las
    columnas de la tabla.

    """

    def __init__(self, headers: Iterable[str]) -> None:
        self.headers = list(headers)
        self.nodes = {}
        self.master = self
        self.parent = None
        self.children = []

    def append(
        self, title: str, id: str | None = None, *, values: str = "VALUE", order: Any = None
    ) -> TableNode:
        """Añade un nodo a la tabla.

        Si se trata de añadir un nodo cuyo ID ya exista, no creará ni añadirá
        un nuevo nodo y devolverá el ya existente.

        """
        id = id or title
        if id in self.nodes:
            return self.nodes[id]

        node = TableNode(self, title, id, values=values, order=order)
        self.nodes[id] = node
        self.children.append(node)
        return node

    def __getitem__(self, id: str) -> TableNode:
        """Devuelve un nodo con el ID indicado que esté subordinado a la tabla.

        Si no lo encuentra, lanzará un KeyError.

        """
        if id in self.nodes:
            return self.nodes[id]
        raise KeyError(f"No se ha encontrado ningún nodo con el ID '{id}'.")

    def __iter__(self) -> Iterable[TableNode]:
        """Devuelve un iterador sobre los nodos de la tabla, ordenados."""
        return iter(sorted(self.children, key=lambda node: node.order))

    def __str__(self) -> str:
        return "\n".join(str(node) for node in self)


if __name__ == "__main__":
    # TESTING

    # Generando datos aleatorios
    events = []
    flows = ["orig", "dest"]
    for _ in range(100):
        acc = random.choice(["Ingresos", "Básicos", "Personales", "Hucha", "Reserva", "Inversión"])
        random.shuffle(flows)
        amount = random.uniform(1, 3000)
        events.append({"account": acc, flows[0]: acc, flows[1]: "Contraparte", "amount": amount})

    table = TableBuilder(["A", "B", "C"])
    table.append("Activos", values="SUM_CHILDREN")
    table["Activos"].append("Corrientes", "COR", values="SUM_CHILDREN")
    table["Activos"].append("Financieros", "FIN", values="SUM_CHILDREN")
    table.append("Pasivos", values="SUM_CHILDREN")
    for event in events:
        account = event["account"]
        if account == event["orig"]:
            amount = -event["amount"]
        else:
            amount = +event["amount"]

        if account == "Inversión":
            category = random.choice(["Planes de pensiones", "Fondos indexados"])
            concept = random.choice(["Mi plan", "Mi fondo"])
            table["FIN"].append(category, values="SUM_CHILDREN")
            target = table["FIN"][category].append(concept, values="VALUE")
        else:
            if account in ("Hucha", "Reserva"):
                category = "Ahorro"
                order = 2
            else:
                category = "Caja"
                order = 1
            table["COR"].append(category, values="SUM_CHILDREN", order=order)
            target = table["COR"][category].append(account, values="VALUE")
        for key in ("A", "B", "C"):
            if key == "A":
                target.values[key] += amount
            elif key == "B":
                target.values[key] += amount * 0.1
            else:
                target.values[key] += amount * 1.25

        print(table)
        print("\n--------------------------------------------------\n")
