# Python 3.10.11
# Creado: 28/02/2024
"""Módulo que define la clase 'TableBuilder', que permite crear tablas de datos
jerárquicas que luego pueden ser exportadas a distintos formatos.

La clase principal es 'TableBuilder', que gestiona la creación de la tabla y
mantiene las 'TableRow' que la componen. Ambas clases heredan de 'Node', para
permitir la jerarquización de las filas de la tabla.

"""
from __future__ import annotations

import random
from types import MappingProxyType
from typing import Any, Iterable, Literal


class _GUARD_CLASS:
    pass


_GUARD = _GUARD_CLASS()


class Node:
    """Clase que representa un nodo de una estructura de árbol.

    Proporciona los atributos típicos 'parent' y 'children', y métodos para
    crear y gestionar los nodos hijos.

    En concreto, los atributos son:
        - id: el identificador único del nodo. No puede haber dos nodos con el
            mismo ID en la misma estructura.
        - parent: el nodo padre del nodo actual.
        - master: el nodo raíz de la estructura.
        - children: una lista de nodos hijos del nodo actual.
        - siblings: una lista de nodos hermanos del nodo actual, sin incluir
            al nodo actual.
        - order_key: la clave para ordenar los nodos hijos. Si no se indica,
            se utilizará el orden de creación.

    Y los métodos disponibles son:
        - append: añade un nodo hijo al nodo actual.
        - get: devuelve un nodo hijo con el ID indicado. También permite
            devolver cualquier nodo subordinado al nodo actual. Este último
            comportamiento se obtiene también accediendo en modo lista al nodo.
        - has_children: indica si el nodo tiene hijos o no.
        - has_grandchildren: indica si el nodo tiene nietos o no.
        - __iter__: devuelve un iterador sobre los nodos hijos del nodo,
            ordenados.

    El constructor requiere, al menos, el nodo padre del nodo actual y el ID
    del nuevo nodo. Si se quiere indicar que el nodo es raíz de una nueva
    estructura, se debe indicar explícitamente con 'None'. Opcionalmente, se
    puede indicar la clave de ordenación de los nodos hijos mediante
    'order_key'.

    """

    ORDER_INDEX = 100

    def __init__(self, parent: Node | None, id: Any, *, order_key: Any = None):
        self.id = id
        self.parent = parent
        self.children = []
        if self.parent is None:
            self.master = self
        else:
            self.master = parent.master
            self.parent.children.append(self)
        if order_key:
            self.order_key = order_key
        else:
            self.order_key = Node.ORDER_INDEX
            Node.ORDER_INDEX += 1

    @property
    def siblings(self) -> Iterable[Node]:
        """Devuelve la lista de nodos hermanos del nodo actual, SIN contar el
        nodo actual.

        """
        return [child for child in self.parent.children if child != self]

    @property
    def generation(self) -> int:
        """Devuelve la generación del nodo en la jerarquía del árbol.

        La generación de un nodo raíz es 0, y la de sus hijos es 1, y así
        sucesivamente.

        """
        generation = 0
        parent = self.parent
        while parent:
            generation += 1
            parent = parent.parent
        return generation

    def has_children(self) -> bool:
        """Indica si el nodo tiene hijos o no."""
        return bool(self.children)

    def has_grandchildren(self) -> bool:
        """Indica si el nodo tiene nietos o no."""
        return any(child.has_children() for child in self.children)

    # Creación y gestión de nodos hijos
    def append(self, id: Any, *args: Any, **kwargs: Any) -> None:
        """Añade un nodo hijo al nodo actual, y lo devuelve.

        El ID del nuevo nodo no debe existir en la estructura actual. Si lo
        hace, este método no hará nada y devolverá el nodo ya existente.

        """
        if id in self:
            return self[id]
        return self.__class__(self, id, *args, **kwargs)

    def get(self, id: Any, fallback: Any = _GUARD, *, only_children: bool = True) -> Node:
        """Devuelve un nodo hijo con el ID indicado.

        Se puede proporcionar un valor por defecto para devolver en caso de no
        encontrar el nodo. Si no se proporciona y no se encuentra el nodo, se
        lanzará un KeyError.

        Si se quiere buscar cualquier nodo subordinado al nodo actual, se debe
        indicar 'only_children' como False.

        """
        if only_children:
            for child in self.children:
                if child.id == id:
                    return child
            if fallback is _GUARD:
                raise KeyError(f"No se ha encontrado ningún nodo con el ID '{id}'.")
            return fallback
        else:
            found = None
            for child in self.children:
                if child.id == id:
                    return child
                elif child.has_children():
                    found = child.get(id, fallback=None, only_children=False)
                    if found:
                        return found
            if fallback is _GUARD:
                raise KeyError(f"No se ha encontrado ningún nodo con el ID '{id}'.")
            return fallback

    def __getitem__(self, id: Any) -> Node:
        """Sinónimo para 'get(id, only_children=False)'."""
        return self.get(id, only_children=False)

    def __contains__(self, id: Any) -> bool:
        """Indica si el nodo actual contiene un nodo con el ID indicado."""
        try:
            self.get(id, only_children=False)
        except KeyError:
            return False
        return True

    def __iter__(self) -> Iterable[Node]:
        """Devuelve un iterador sobre los nodos hijos del nodo, ordenados."""
        return iter(sorted(self.children, key=lambda node: node.order_key))

    def __str__(self) -> str:
        return f"Node({self.generation}, {self.id})"


# OLD #
class TableRow(Node):
    """Clase que representa una fila de una tabla de datos.

    Se compone de un título ('title') y de un diccionario de valores ('values')
    que, en función del tipo de valor que almacene la fila ('formula'), pueden
    ser datos directos, o agregaciones de datos de otras filas.

    Existen tres tipos de fórmulas aceptables:

        - None: opción por defecto, los valores son datos directos.

        - Operaciones predefinidas: se preceden de '@', y son operaciones
            típicas de agregación de datos entre nodos de la tabla.
            * "@SUM_CHILDREN": los valores son la suma de los valores de sus
                nodos hijos.
            * "@SUM_SIBLINGS": los valores son la suma de los valores de sus
                nodos hermanos.

        - Operaciones libres: cualquier otra cadena que no comience por '@'
            se considerará una fórmula libre, que admite cualquier operación
            que sería admitible por una fórmula de Excel. Para hacer referencia
            a nodos de la tabla, se utilizará el ID del nodo entre llaves '{}'.

    Además, hereda de 'Node' para permitir la jerarquización de las filas de la
    tabla.

    El constructor recibe en orden, el nodo padre de la fila, el ID de la fila,
    el título de la fila, y opcionalmente, el tipo de valores que gestionará la
    fila.

    Si no se proporciona un título para la fila, se utilizará el ID como tal.

    """

    def __init__(
        self,
        parent: Node,
        id: str,
        title: str | None = None,
        *,
        formula: None | str = None,
        order_key: Any = None,
    ):
        super().__init__(parent, id, order_key=order_key)
        self.title = title or id
        self.formula = formula
        self._values = {key: 0 for key in parent.master.headers}

    @property
    def values(self) -> dict[str, float] | MappingProxyType[str, float]:
        """Devuelve los valores de la fila, en función del tipo de valores que
        gestiona.

        En caso de no gestionar valores directamente, se devolverá una vista
        del diccionario, para que no se puedan modificar.

        """
        if self.formula is None:
            for key in self._values:
                self._values[key] = round(self._values[key], 2)
            return self._values
        elif self.formula == "@SUM_CHILDREN":
            for key in self._values:
                self._values[key] = round(sum(child.values[key] for child in self.children), 2)
        elif self.formula == "@SUM_SIBLINGS":
            for key in self._values:
                self._values[key] = round(sum(sibling.values[key] for sibling in self.siblings), 2)
        elif self.formula.startswith("@"):
            raise ValueError(f"Fórmula predefinida no reconocida: '{self.formula}'")
        else:
            # TODO: Implementar fórmulas libres
            pass
        return MappingProxyType(self._values)

    def __str__(self) -> str:
        id = str(self.id)[:10]
        title = f"{'  ' * self.generation}{self.title}"
        return f"[{id:*>10}] {title: <40} | {self.values}"


class TableBuilder(Node):
    """Clase que gestiona la creación de una tabla de datos jerárquica.

    Esta clase actúa como nodo maestro de la estructura, y mantiene una lista
    de nodos hijos que representan las filas de la tabla. Además, define las
    cabeceras de las columnas de la tabla.

    El constructor recibe un iterable con las cabeceras de las columnas de la
    tabla. Opcionalmente, se puede dar también un título para la tabla en
    conjunto.

    """

    def __init__(self, headers: Iterable[str], *, title: str = "Tabla") -> None:
        super().__init__(None, "MASTER")
        self.title = title
        self.headers = list(headers)

    def append(self, id: str, *args, **kwargs) -> TableRow:
        """Añade una fila a la tabla."""
        if id in self:
            return self[id]
        return TableRow(self, id, *args, **kwargs)

    def __iter__(self) -> Iterable[TableRow]:
        """Devuelve un iterador sobre las filas de la tabla, iterando también
        sobre toda la descendencia de sus nodos hijos, si los tiene.

        """
        node_list = []
        for child in sorted(self.children, key=lambda node: node.order_key):
            node_list = self._add_node(child, node_list)
        return iter(node_list)

    def _add_node(self, node: Node, node_list: list[Node]) -> list[Node]:
        """Añade un nodo y toda su descendencia a una lista."""
        node_list.append(node)
        for child in node:
            node_list = self._add_node(child, node_list)
        return node_list

    def __str__(self) -> str:
        s = [f"Tabla: {self.title}"]
        for node in self:
            s.append(str(node))
        return "\n".join(s)


if __name__ == "__xmain__":
    table = TableBuilder(["A", "B", "C"])
    table.append("Frutas", formula="@SUM_CHILDREN")
    f = table["Frutas"].append("Manzana")
    table["Frutas"].append("Pera")
    f.values["A"] = 10
    f.values["B"] = 20
    f.values["C"] = 30
    table["Frutas"]["Pera"].values["A"] = 5
    table["Frutas"]["Pera"].values["B"] = 50
    table["Frutas"]["Pera"].values["C"] = 500
    table.append("Verduras", formula="@SUM_CHILDREN")
    f = table["Frutas"].append("Manzana")
    f.values["B"] += 1000
    print(table)


if __name__ == "__main__":
    # TESTING

    # Generando datos aleatorios
    events = []
    flows = ["orig", "dest"]
    for _ in range(100):
        acc = random.choice(["Ingresos", "Básicos", "Personales", "Hucha", "Reserva", "Inversión"])
        random.shuffle(flows)
        amount = round(random.uniform(1, 3000), 2)
        events.append({"account": acc, flows[0]: acc, flows[1]: "Contraparte", "amount": amount})

    table = TableBuilder(["A", "B", "C"])
    table.append("Activos", formula="@SUM_CHILDREN")
    table["Activos"].append("COR", "Corrientes", formula="@SUM_CHILDREN")
    table["Activos"].append("FIN", "Financieros", formula="@SUM_CHILDREN")
    table.append("Pasivos", formula="@SUM_CHILDREN")
    for event in events:
        account = event["account"]
        if account == event["orig"]:
            amount = -event["amount"]
        else:
            amount = +event["amount"]

        if account == "Inversión":
            category = random.choice(["Planes de pensiones", "Fondos indexados"])
            concept = random.choice(["Mi plan", "Mi fondo"])
            table["FIN"].append(category, formula="@SUM_CHILDREN")
            target = table["FIN"][category].append(concept, formula=None)
        else:
            if account in ("Hucha", "Reserva"):
                category = "Ahorro"
                order = 2
            else:
                category = "Caja"
                order = 1
            table["COR"].append(category, formula="@SUM_CHILDREN", order_key=order)
            target = table["COR"][category].append(account, formula=None)
        for key in ("A", "B", "C"):
            if key == "A":
                target.values[key] += amount
            elif key == "B":
                target.values[key] += amount * 0.1
            else:
                target.values[key] += amount * 1.25

    print(table)
