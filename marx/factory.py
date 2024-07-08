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
        super().__setattr__("_baseclass", None)
        super().__setattr__("_all", None)
        super().__setattr__("_status", None)
        super().__setattr__("_changes", None)
        super().__setattr__("_handled", None)
        super().__setattr__("_inactive_are_visible", None)
        super().__setattr__("_parent", None)
        self._baseclass = base
        self._all = {}
        self._status = {}  # 0: eliminado, 1: activo, 2: modificado
        self._changes = {}  # {<id>: [<set de atributos que han cambiado>]}
        self._handled = []  # IDs de los objetos manejados por esta lista
        self._inactive_are_visible = False
        self._parent = None  # referencia a la lista padre, si existe

    # Privados

    @property
    def _visible(self) -> list[int]:
        """IDs de los objetos visibles manejados por esta lista"""
        if self._inactive_are_visible:
            return [id for id in self._handled]
        else:
            return [id for id in self._handled if self._status[id] > 0]

    def _append(self, item: FactoryItem) -> int:
        Factory.GLOBAL_INDEX += 1
        id = Factory.GLOBAL_INDEX
        self._all[id] = item
        self._status[id] = 1
        self._handled.append(id)
        return id

    def _create_subset(
        self, ids: list[int], *, inactive_are_visible: bool | None = None
    ) -> Factory[FactoryItem]:
        # copia todos los objetos y estados, pero sólo maneja los IDs dados
        subset = Factory(self._baseclass)
        subset._all = self._all
        subset._status = self._status
        subset._changes = self._changes
        subset._handled = ids
        if inactive_are_visible is None:
            subset._inactive_are_visible = self._inactive_are_visible
        else:
            subset._inactive_are_visible = inactive_are_visible
        subset._parent = self
        return subset

    # Públicos

    @property
    def all(self) -> Factory[FactoryItem]:
        """Subconjunto con todos los objetos de la lista, activos o no,
        manejados por esta lista o no

        """
        return self._create_subset(self._all.keys(), inactive_are_visible=True)

    @property
    def any(self) -> Factory[FactoryItem]:
        """Subconjunto con todos los objetos de la lista, activos o no,
        manejados por esta lista

        """
        return self._create_subset(self._handled, inactive_are_visible=True)

    @property
    def active(self) -> Factory[FactoryItem]:
        """Subconjunto con todos los objetos visibles de la lista"""
        return self._create_subset(self._handled, inactive_are_visible=False)

    @property
    def meta_deleted(self) -> Iterator[FactoryItem]:
        """Itera sobre los objetos eliminados"""
        return (self._all[id] for id in self._handled if self._status[id] == 0)

    @property
    def meta_changed(self) -> Iterator[tuple[FactoryItem, list[str]]]:
        """Itera sobra los objetos modificados, junto con la lista de qué
        atributos han cambiado

        """
        return (
            (self._all[id], list(self._changes[id]))
            for id in self._handled
            if self._status[id] == 2
        )

    def new(self, *args: Any, **kwargs: Any) -> Factory[FactoryItem]:
        """Crea un nuevo objeto industrializado, usando el constructor de su
        base y los argumentos dados

        Devuelve un subconjunto sólo con el objeto creado.

        """
        try:
            item = self._baseclass(*args, **kwargs)
        except TypeError:
            raise TypeError(
                f"[Factory] No se puede crear un objeto de tipo '{self._baseclass.__name__}' con los argumentos dados."
            ) from None
        id = self._append(item)
        return self._create_subset([id])

    def register(self, item: FactoryItem) -> Factory[FactoryItem]:
        """Registra un objeto en la lista y lo industrializa

        El objeto debe ser del mismo tipo que la base de la lista, de lo
        contrario, se lanza una excepción.

        Devuelve un subconjunto sólo con el objeto registrado.

        """
        if not isinstance(item, self._baseclass):
            raise TypeError(
                f"[Factory] El objeto debe ser de tipo '{self._baseclass.__name__}', no '{type(item).__name__}'."
            )
        id = self._append(item)
        return self._create_subset([id])

    def fallback(self, *args: Any, **kwargs: Any) -> Factory[FactoryItem]:
        """Crea o registra un nuevo objeto industrializado, y lo asigna a
        esta lista, si esta vacía o no tiene objetos visibles

        Si sólo se incluye un argumento y es del tipo de la base, se registra
        el objeto mediante 'register'. De lo contrario, se crea un objeto nuevo
        mediante 'new'.

        """
        if self.empty():
            if not kwargs and len(args) == 1 and isinstance(args[0], self._baseclass):
                return self._parent.register(args[0])
            return self._parent.new(*args, **kwargs)

    def select(self, *attrs: str) -> list[list[Any]]:
        """Devuelve una matriz con los valores de los atributos dados de los
        objetos visibles

        Si un atributo no existe en un objeto, se asigna None en su lugar

        """
        return [[getattr(self._all[id], attr, None) for attr in attrs] for id in self._visible]

    def __getattr__(self, attr: str) -> list[Any]:
        """Sugarcoat para 'select', pero devuelve una lista simple"""
        return [row[0] for row in self.select(attr)]

    def update(self, **kwargs: Any) -> None:
        """Actualiza los atributos de todos los objetos visibles según los
        argumentos dados

        Si se usan argumentos que no existen, se ignoran.

        """
        for id in self._visible:
            for attr, value in kwargs.items():
                if hasattr(self._all[id], attr):
                    setattr(self._all[id], attr, value)
                    self._status[id] = self._status[id] and 2
                    if id not in self._changes:
                        self._changes[id] = set()
                    self._changes[id].add(attr)

    def __setattr__(self, attr: str, value: Any) -> None:
        """Sugarcoat para 'update'"""
        # 'attr' no debe existir en 'Factory'
        if attr not in self.__dict__:
            self.update(**{attr: value})
        else:
            super().__setattr__(attr, value)

    def delete(self) -> None:
        """Marca todos los objetos visibles para eliminación"""
        for id in self._visible:
            self._status[id] = 0

    def pull(self) -> list[FactoryItem]:
        """Devuelve una lista con los objetos visibles"""
        return [self._all[id] for id in self._visible]

    def pullone(self) -> FactoryItem | None:
        """Devuelve un sólo objeto, el primero de los que estén visibles

        Si no hay objetos visibles, devuelve None

        """
        try:
            return self._all[next(iter(self._visible))]
        except StopIteration:
            return None

    def __iter__(self) -> Iterator[Factory[FactoryItem]]:
        """Itera sobre los objetos visibles

        Devuelve subconjuntos con un sólo objeto, nunca el objeto directamente

        """
        yield from (self._create_subset([id]) for id in self._visible)

    def sort(self, attr: str, *attrs: str, reverse: bool = False) -> Factory[FactoryItem]:
        """Genera un nuevo subconjunto con los objetos visibles, ordenados por
        los atributos dados

        """
        return self._create_subset(
            list(
                sorted(
                    self._visible,
                    key=lambda id: [getattr(self._all[id], a) for a in (attr, *attrs)],
                    reverse=reverse,
                )
            )
        )

    def subset(self, *funcs: Callable[[FactoryItem], bool], **kwargs: Any) -> Factory[FactoryItem]:
        """Crea un subconjunto de la lista, filtrando los objetos según los
        argumentos dados

        'funcs' pueden ser funciones que reciban un objeto y devuelvan True o
        False según si este debe ser incluido en el subconjunto.

        'kwargs' se puede usar para filtrar por atributos específicos, donde la
        clave es el nombre del atributo y el valor es el valor que debe tener.

        """
        # kwargs -> funcs
        for attr, value in kwargs.items():
            funcs += (lambda item, a=attr, v=value: getattr(item, a) == v,)
        # filtrar
        ids = [id for id in self._visible if all(f(self._all[id]) for f in funcs)]
        return self._create_subset(ids)

    def empty(self) -> bool:
        """Devuelve True si no hay objetos visibles"""
        return not bool(self._visible)

    def __len__(self) -> int:
        """Devuelve la cantidad de objetos visibles"""
        return len(self._visible)

    def __getitem__(self, key: int | slice) -> Factory[FactoryItem]:
        """Devuelve un subconjunto con el objeto en la posición dada"""
        if isinstance(key, int):
            return self._create_subset([self._visible[key]])
        elif isinstance(key, slice):
            return self._create_subset(self._visible[key])

    # Representación

    def __repr__(self) -> str:
        lv = len(self._visible)
        lh = len(self._handled)
        return f"Factory({self._baseclass.__name__}, v: {lv}, h: {lh})"

    def __str__(self) -> str:
        return repr(self)

    def show(self) -> None:
        print("---")
        print(self)
        id_zeros = len(str(len(self._handled)))
        for id in self._handled:
            status = {0: "DEL", 1: "ACT", 2: "MOD"}[self._status[id]]
            print(f" ->  {id:0>{id_zeros}} | {status} | {self._all[id]!r}")
        print("---")

    # Debugging

    def dbg_show(self, title: str = "<GENERIC>") -> None:
        print(title)
        print(f"  Base: {self._baseclass.__name__}")
        print(f"  Objetos visibles: {len(self)}")
        print(f"  Objetos activos: {len(self.active)}")
        print(f"  Objetos manejados: {len(self.any)}")
        print(f"  Objetos totales: {len(self.all)}")
        print(f"  Objetos:")
        for id in self._visible:
            print(f"    {id} | {self._status[id]} | {self._all[id]!r}")
        print()
