# Python 3.10.11
# Creado: 02/08/2024
"""Clase auxiliar para gestionar listas de objetos industrializados

Un objeto "industrializado" es todo objeto que tenga valor al usarse en listas
de objetos iguales, tratándose a todos como un conjunto, de tal manera que se
admita modificación y eliminación en masa, y registro de cambios.

"""

from __future__ import annotations

from typing import Any, Callable, Generic, Iterator, TypeVar


FactoryItem = TypeVar("FactoryItem")


class Factory(Generic[FactoryItem]):
    """Lista para manejar objetos industrializados"""

    GLOBAL_INDEX = 0

    def __init__(self, base: type[FactoryItem]) -> None:
        super().__setattr__("_base", None)
        super().__setattr__("_items", None)
        super().__setattr__("_status", None)
        super().__setattr__("_subset", None)
        self._base = base
        self._items = {}
        self._status = {}  # 0: eliminado, 1: activo, 2: modificado
        self._subset = []  # subconjuntos de objetos manejados por esta lista

    # Privados

    @property
    def _active(self) -> list[int]:
        """Devuelve los IDs de los objetos activos

        Un objeto está activo si es manejado por esta lista, y no está marcado
        para eliminación (status == 0)

        """
        return [id for id in self._items if self._status[id] > 0 and id in self._subset]

    def _append(self, item: FactoryItem) -> int:
        Factory.GLOBAL_INDEX += 1
        id = Factory.GLOBAL_INDEX
        self._items[id] = item
        self._status[id] = 1
        self._subset.append(id)
        return id

    def _create_subset(self, *ids: int) -> Factory[FactoryItem]:
        # copia todos los objetos y estados, pero sólo maneja los IDs dados
        subset = Factory(self._base)
        subset._items = self._items
        subset._status = self._status
        subset._subset = ids
        return subset

    # Públicos

    def new(self, *args: Any, **kwargs: Any) -> Factory[FactoryItem]:
        """Crea un nuevo objeto industrializado, usando el constructor de su
        base y los argumentos dados

        Devuelve un subconjunto sólo con el objeto creado

        """
        try:
            item = self._base(*args, **kwargs)
        except TypeError:
            raise TypeError(
                f"[Factory] No se puede crear un objeto de tipo '{self._base.__name__}' con los argumentos dados."
            ) from None
        id = self._append(item)
        return self._create_subset(id)

    def register(self, item: FactoryItem) -> Factory[FactoryItem]:
        """Registra un objeto en la lista y lo industrializa

        El objeto debe ser del mismo tipo que la base de la lista, de lo
        contrario, se lanza una excepción.

        Devuelve un subconjunto sólo con el objeto registrado.

        """
        if not isinstance(item, self._base):
            raise TypeError(
                f"[Factory] El objeto debe ser de tipo '{self._base.__name__}', no '{type(item).__name__}'."
            )
        id = self._append(item)
        return self._create_subset(id)

    def fallback(self, *args: Any, **kwargs: Any) -> Factory[FactoryItem]:
        """Crea o registra un nuevo objeto industrializado, y lo asigna a
        esta lista, si esta vacía o no tiene objetos activos

        Si sólo se incluye un argumento y es del tipo de la base, se registra
        el objeto mediante 'regsiter'. De lo contrario, se crea un objeto nuevo
        mediante 'new'.

        """
        if self.empty():
            if not kwargs and len(args) == 1 and isinstance(args[0], self._base):
                return self.register(args[0])
            return self.new(*args, **kwargs)

    def select(self, *attrs: str) -> list[list[Any]]:
        """Devuelve una matriz con los valores de los atributos dados de los
        objetos activos

        Si un atributo no existe en un objeto, se asigna None en su lugar

        """
        return [[getattr(self._items[id], attr, None) for attr in attrs] for id in self._active]

    def __getattr__(self, attr: str) -> list[Any]:
        """Sugarcoat para 'select', pero devuelve una lista simple"""
        return [row[0] for row in self.select(attr)]

    def update(self, **kwargs: Any) -> None:
        """Actualiza los atributos de todos los objetos activos según los
        argumentos dados

        Si se usan argumentos que no existen, se ignoran.

        """
        for id in self._active:
            for attr, value in kwargs.items():
                if hasattr(self._items[id], attr):
                    setattr(self._items[id], attr, value)

    def __setattr__(self, attr: str, value: Any) -> None:
        """Sugarcoat para 'update'"""
        # 'attr' no debe existir en 'Factory'
        if not hasattr(self, attr):
            self.update(**{attr: value})
        else:
            super().__setattr__(attr, value)

    def delete(self) -> None:
        """Marca todos los objetos activos para eliminación"""
        for id in self._active:
            self._status[id] = 0

    def __del__(self) -> None:
        """Marca todos los objetos activos para eliminación"""
        self.delete()

    def pull(self) -> list[FactoryItem]:
        """Devuelve una lista con los objetos activos"""
        return [self._items[id] for id in self._active]

    def pullone(self) -> FactoryItem | None:
        """Devuelve un sólo objeto, el primero de los que estén activos

        Si no hay objetos activos, devuelve None

        """
        try:
            return self._items[next(iter(self._active))]
        except StopIteration:
            return None

    def __iter__(self) -> Iterator[Factory[FactoryItem]]:
        """Itera sobre los objetos activos

        Devuelve subconjuntos con un sólo objeto, nunca el objeto directamente

        """
        yield from (self._create_subset(id) for id in self._active)

    def iter_all(self) -> Iterator[Factory[FactoryItem]]:
        """Itera sobre todos los objetos, activos y marcados para eliminación

        Al igual que '__iter__', devuelve subconjuntos con un sólo objeto

        """
        for id in self._items:
            yield self._create_subset(id)

    def sort(self, attr: str, *attrs: str, reverse: bool = False) -> Factory[FactoryItem]:
        """Genera un nuevo subconjunto con los objetos activos, ordenados por
        los atributos dados

        """
        return self._create_subset(
            *sorted(
                self._active,
                key=lambda id: [getattr(self._items[id], a) for a in (attr, *attrs)],
                reverse=reverse,
            )
        )

    def sort_all(self, attr: str, *attrs: str, reverse: bool = False) -> Factory[FactoryItem]:
        """Genera un nuevo subconjunto con todos los objetos, ordenados por los
        atributos dados

        """
        return self._create_subset(
            *sorted(
                self._items,
                key=lambda id: [getattr(self._items[id], a) for a in (attr, *attrs)],
                reverse=reverse,
            )
        )

    def subset(self, *funcs: Callable[[FactoryItem], bool], **kwargs: Any) -> Factory[FactoryItem]:
        """Crea un subconjunto de la lista, filtrando los objetos según los
        argumentos dados

        'funcs' pueden ser funciones que reciban un objeto y devuelvan True o
        False según si este debe ser incluido en el subconjunto.

        'kwargs' se puede usar para filtrar por atributos específicos, donde la
        clave es el nombre del atributo y el valor es el valor que debe tener.
        En este caso, se puede usar el atributo especial 'meta_status', que
        hace referencia al estado interno del objeto (0: eliminado, 1: activo,
        2: modificado).

        """
        # kwargs -> funcs
        for attr, value in kwargs.items():
            if attr == "meta_status":
                funcs += (lambda item, v=value: self._status[id] == v,)
            else:
                funcs += (lambda item, a=attr, v=value: getattr(item, a) == v,)
        # filtrar
        ids = [id for id in self._active if all(f(self._items[id]) for f in funcs)]
        return self._create_subset(*ids)

    def empty(self) -> bool:
        """Devuelve True si no hay objetos activos"""
        return not bool(self._active)

    def __len__(self) -> int:
        """Devuelve la cantidad de objetos activos"""
        return len(self._active)

    # Representación

    def __repr__(self) -> str:
        return f"Factory({self._base.__name__}, {len(self)} objetos activos)"
