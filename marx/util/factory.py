# Python 3.10.11
# Creado: 02/08/2024
"""Clase auxiliar para gestionar listas de objetos industrializados

Un objeto "industrializado" es todo objeto que tenga valor al usarse en listas
de objetos iguales, tratándose a todos como un conjunto, de tal manera que se
admita modificación y eliminación en masa, y registro de cambios.

"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Generic, Iterator, TypeVar

FactoryItem = TypeVar("FactoryItem")


@dataclass
class ItemMetadata:
    """Metadatos de un objeto industrializado"""

    iid: int  # ID interno
    item: FactoryItem
    status: int = 1  # 0: eliminado, 1: activo, 2: modificado
    changes: set[str] = field(default_factory=set)


class Factory(Generic[FactoryItem]):
    """Lista para manejar objetos industrializados"""

    GLOBAL_INDEX = 0

    def __init__(self, base: type[FactoryItem]) -> None:
        super().__setattr__("base", None)
        super().__setattr__("_items", None)
        super().__setattr__("_handled", None)
        super().__setattr__("_parent", None)
        self.base = base
        self._items = {}  # ID -> ItemMetadata
        self._handled = []  # IDs de los objetos manejados por esta lista
        self._parent = None  # referencia a la lista padre, si existe

    # Internos

    @property
    def _active(self) -> Iterator[int]:
        """IDs de los objetos activos, manejados por esta lista"""
        yield from (id for id in self._handled if self._items[id].status >= 1)

    def _append(self, item: FactoryItem) -> int:
        Factory.GLOBAL_INDEX += 1
        id = Factory.GLOBAL_INDEX
        self._items[id] = ItemMetadata(id, item)
        self._handled.append(id)
        return id

    def _create_subset(self, include_ids: list[int]) -> Factory[FactoryItem]:
        # copia todos los objetos y estados, pero sólo maneja los IDs dados
        subset = Factory(self.base)
        subset._items = self._items
        subset._handled = include_ids
        subset._parent = self
        return subset

    # Información

    def __len__(self) -> int:
        """Devuelve la cantidad de objetos activos manejados por esta lista"""
        return len(list(self._active))

    def is_empty(self) -> bool:
        """Devuelve True si no hay objetos activos manejados por esta lista"""
        return len(self) == 0

    # Iteración

    def active(self) -> Iterator[Factory]:
        """Itera sobre los objetos activos manejados por esta lista"""
        yield from (self._create_subset([id]) for id in self._active)

    def __iter__(self) -> Iterator[Factory]:
        """Itera sobre los objetos activos manejados por esta lista"""
        yield from self.active()

    def all(self) -> Iterator[Factory]:
        """Itera sobre todos los objetos"""
        yield from (self._create_subset([id]) for id in self._items)

    # Iteración especial

    def meta_deleted(self) -> Iterator[FactoryItem]:
        """Itera sobre los objetos eliminados"""
        yield from (
            self._items[id].item for id in self._handled if self._items[id].status == 0
        )

    def meta_changes(self) -> Iterator[tuple[FactoryItem, list[str]]]:
        """Itera sobra los objetos modificados, junto con la lista de qué
        atributos han cambiado

        """
        yield from (
            (self._items[id].item, list(self._items[id].changes))
            for id in self._handled
            if self._items[id].status == 2
        )

    def meta_force_update(self, *args) -> None:
        """Fuerza a que el objeto se actualice sobre '*args'"""
        for id in self._handled:
            meta = self._items[id]
            meta.status = 2
            for arg in args:
                meta.changes.add(arg)

    # Adición, modificación y eliminación

    def new(self, *args: Any, **kwargs: Any) -> Factory[FactoryItem]:
        """Crea un nuevo objeto industrializado, usando el constructor de su
        base y los argumentos dados

        Devuelve un subconjunto sólo con el objeto creado.

        """
        try:
            item = self.base(*args, **kwargs)
        except TypeError:
            raise TypeError(
                f"[Factory] No se puede crear un objeto de tipo '{self.base.__name__}' con los argumentos dados."
            ) from None
        id = self._append(item)
        return self._create_subset([id])

    def register(self, item: FactoryItem) -> Factory[FactoryItem]:
        """Registra un objeto en la lista y lo industrializa

        El objeto debe ser del mismo tipo que la base de la lista, de lo
        contrario, se lanza una excepción.

        Devuelve un subconjunto sólo con el objeto registrado.

        """
        if not isinstance(item, self.base):
            raise TypeError(
                f"[Factory] El objeto debe ser de tipo '{self.base.__name__}', no '{type(item).__name__}'."
            )
        id = self._append(item)
        return self._create_subset([id])

    def fallback(self, *args: Any, **kwargs: Any) -> Factory[FactoryItem]:
        """Crea o registra un nuevo objeto industrializado, y lo asigna a
        esta lista, si esta vacía o no tiene objetos activos

        Si sólo se incluye un argumento y es del tipo de la base, se registra
        el objeto mediante 'register'. De lo contrario, se crea un objeto nuevo
        mediante 'new'.

        """
        if self.is_empty():
            if not kwargs and len(args) == 1 and isinstance(args[0], self.base):
                return self._parent.register(args[0])
            return self._parent.new(*args, **kwargs)
        return self

    def update(self, **kwargs: Any) -> None:
        """Actualiza los atributos de todos los objetos activos según los
        argumentos dados

        Si se usan argumentos que no existen, se ignoran.

        """
        for id in self._active:
            meta = self._items[id]
            for attr, value in kwargs.items():
                if hasattr(meta.item, attr):
                    setattr(meta.item, attr, value)
                    meta.status = 2
                    meta.changes.add(attr)

    def __setattr__(self, attr: str, value: Any) -> None:
        """Sugarcoat para 'update'"""
        # 'attr' no debe existir en 'Factory'
        if attr not in self.__dict__:
            self.update(**{attr: value})
        else:
            super().__setattr__(attr, value)

    def delete(self) -> None:
        """Marca todos los objetos visibles para eliminación"""
        for id in self._active:
            self._items[id].status = 0

    # Selección y extracción

    def select(self, *attrs: str) -> list[list[Any]]:
        """Devuelve una matriz con los valores de los atributos dados de los
        objetos activos

        Si un atributo no existe en un objeto, se asigna None en su lugar

        """
        return [
            [getattr(self._items[id].item, attr, None) for attr in attrs]
            for id in self._active
        ]

    def __getattr__(self, attr: str) -> Any | list[Any]:
        """Sugarcoat para 'select'

        Devuelve una lista simple si hay varios objetos activos, o
        directamente el valor si sólo hay uno.

        """
        lst = [row[0] for row in self.select(attr)]
        return lst[0] if len(lst) == 1 else lst

    def pull(self) -> list[FactoryItem]:
        """Devuelve una lista con los objetos activos"""
        return [self._items[id].item for id in self._active]

    def pullone(self) -> FactoryItem | None:
        """Devuelve un sólo objeto, el primero de los que estén activos

        Si no hay objetos activos, devuelve None

        """
        if self.is_empty():
            return None
        return self._items[next(self._active)].item

    # Filtrado y ordenamiento

    def subset(
        self, *funcs: Callable[[FactoryItem], bool], **kwargs: Any
    ) -> Factory[FactoryItem]:
        """Crea un subconjunto de la lista, filtrando los objetos según los
        argumentos dados

        'funcs' pueden ser funciones que reciban un objeto y devuelvan True o
        False según si este debe ser incluido en el subconjunto.

        'kwargs' se puede usar para filtrar por atributos específicos, donde la
        clave es el nombre del atributo y el valor es el valor que debe tener.

        Sólo filtra objetos activos. Si no se indica ningún filtro, se devuelve
        una lista vacía.

        """
        # kwargs -> funcs
        for attr, value in kwargs.items():
            funcs += (lambda item, a=attr, v=value: getattr(item, a) == v,)
        # no hay filtros
        if not funcs:
            return self._create_subset([])
        # filtrar
        ids = [id for id in self._active if all(f(self._items[id].item) for f in funcs)]
        return self._create_subset(ids)

    def sort(self, *attrs: str, reverse: bool = False) -> Factory[FactoryItem]:
        """Crea un subconjunto, copia de esta lista, pero con los elementos
        ordenados según los atributos dados

        Si no se indican atributos, se usarán los métodos propios de los
        objetos manejados. Si se indica 'reverse=True', se ordenará de manera
        descendente.

        """
        if attrs:

            def key(id):
                return tuple(getattr(self._items[id].item, attr) for attr in attrs)

        else:

            def key(id):
                return self._items[id].item

        ids = sorted(self._handled, key=key, reverse=reverse)
        return self._create_subset(ids)

    # Rollback

    def rollback(self, *, deleted: bool = True, changes: bool = True) -> None:
        """Revierte los cambios en los objetos manejados por esta lista

        Se puede indicar que no se reviertan los objetos eliminados o los
        modificados, usando 'deleted' y 'changes' respectivamente.

        """
        if deleted:
            for id in self._handled:
                if self._items[id].status == 0:
                    self._items[id].status = 1
        if changes:
            for id in self._handled:
                if self._items[id].status == 2:
                    self._items[id].status = 1
                    self._items[id].changes.clear()

    # Operaciones entre listas

    def join(self, other: Factory[FactoryItem]) -> Factory[FactoryItem]:
        """Une dos listas de objetos industrializados, manteniendo la base de
        la primera

        Los objetos de la segunda lista se añaden a la primera, y se devuelve
        la primera lista.

        """
        for id in other._handled:
            self._items[id] = other._items[id]
            self._handled.append(id)
        return self

    # Debugging

    def head(self, n: int = 5) -> Factory[FactoryItem]:
        """Devuelve un subconjunto con los primeros 'n' objetos visibles"""
        return self._create_subset(self._handled[:n])

    def tail(self, n: int = 5) -> Factory[FactoryItem]:
        """Devuelve un subconjunto con los últimos 'n' objetos visibles"""
        return self._create_subset(self._handled[-n:])

    def __getitem__(self, key: int | slice) -> Factory[FactoryItem]:
        """Devuelve un subconjunto con el objeto en la posición dada"""
        if isinstance(key, int):
            return self._create_subset([self._handled[key]])
        elif isinstance(key, slice):
            return self._create_subset(self._handled[key])

    # Representación

    def __str__(self) -> str:
        la = len(list(self._active))
        lh = len(self._handled)
        return f"Factory of {self.base.__name__} objects ({la} active, {lh} handled)"

    def show(self) -> None:
        print("---")
        print(self)
        id_zeros = len(str(len(self._handled)))
        for id in self._handled:
            meta = self._items[id]
            status = {0: "DEL", 1: "ACT", 2: "MOD"}[meta.status]
            print(f" ->  {id:0>{id_zeros}} | {status} | {meta.item!s}")
        print("---")

    def dbg_show(self, title: str = "<GENERIC>") -> None:
        print(title)
        print(f"  Base: {self.base.__name__}")
        print(f"  Objetos activos: {len(self.active)}")
        print(f"  Objetos manejados: {len(self.any)}")
        print(f"  Objetos totales: {len(self.all)}")
        print("  Objetos:")
        for id in self._handled:
            print(f"    {id} | {self._status[id]} | {self._items[id]!r}")
        print()
