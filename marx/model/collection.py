# Python 3.10.11
# Creado: 24/01/2024
"""Clase para representar una colección de datos.

Una colección de datos permite almacenar un conjunto de datos de un mismo tipo,
además de crearlos, modificarlos y eliminarlos individual o masivamente desde
la propia interfaz de la colección. También proporciona mecanismos de búsqueda
y filtrado.

"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

from more_itertools import windowed

CollectionEntity = object

# Metadatos de las entidades
# 'source' indica la fuente de la entidad, que puede ser 'new' o 'add'.
# 'status' indica el estado de la entidad, que puede ser 'active' o 'deleted'.
#   Si está en 'deleted' no quiere decir que se haya eliminado realmente, pero
#   se ignora en todos los métodos que afecten a la colección.
# 'changes' es una lista de atributos que han cambiado desde que se incluye la
#   entidad en la colección.
BASE_META = {"source": None, "status": "active", "changes": []}


class Collection:
    """Clase para representar una colección de datos.

    Una colección de datos almacena una cantidad arbitraria de entidades de un
    mismo tipo. Estas entidades pueden crearse, modificarse y eliminarse
    individual o masivamente desde la propia interfaz de la colección. También
    proporciona mecanismos de búsqueda y filtrado.

    Los métodos de manipulación son:
    - new: Crea una nueva entidad, replicando el constructor original.
    - add: Añade una entidad a la colección.
    - update: Actualiza todas las entidades de la colección.
    - delete: Elimina todas las entidades de la colección.

    Además, si se tratan de modificar atributos no propios de 'Collection',
    estos derivarán a los atributos de la entidad, actuando como un 'update'.

    Los métodos de búsqueda y filtrado son:
    - search: Busca una entidad por alguno de sus atributos.
    - get: Obtiene una única entidad por alguno de sus atributos.
    - []: Obtiene una única entidad usando sus claves primarias. Las claves
        primarias se definen durante la construcción del objeto, y se usan
        siempre que no se especifique otro atributo de búsqueda explícito.

    Todos los métodos de búsqueda y filtrado devuelven una nueva colección
    con los resultados obtenidos. Si esta colección estuviera vacía, se
    devuelve None. Si sólo hay un elemento en la colección, se puede usar el
    atributo 'entity' para acceder a él. En este caso, además, si se consultan
    atributos no propios de la colección, estos derivarán al objeto.

    El constructor recibe como principal parámetro la clase de las entidades.
    Además, puede recibir el argumento "pkeys" junto con una lista de atributos
    para usar como claves primarias.

    """

    def __init__(self, base: type, *, pkeys: list[str] | None = None):
        # Como hemos sobrescrito __setattr__, tenemos que inicializar
        # los atributos de forma manual
        super().__setattr__("_base", None)
        super().__setattr__("_iid", None)
        super().__setattr__("_entities", None)
        super().__setattr__("_meta", None)
        super().__setattr__("pkeys", None)

        self._base = base

        self._iid = [0]  # Índice interno de la colección
        self._entities = {}  # iid: entity
        self._meta = {}  # Compartido por todas las colecciones derivadas

        self.pkeys = pkeys or []  # Público, para que se pueda modificar

    @property
    def entity(self) -> CollectionEntity:
        """Devuelve la única entidad de la colección, si solo hay una."""
        if len(self) == 1:
            return next(iter(self._active))[1]
        raise ValueError("La colección no tiene una única entidad.")

    # Interno
    def _append(self, entity: CollectionEntity, **meta) -> int:
        """Añade internamente una entidad.

        Para poder almacenar metadatos sobre las entidades incluso cuando se
        crean colecciones derivadas, existe un ID interno (iid) que se usa
        para identificar a cada entidad.

        Al añadir una nueva entidad, este método automáticamente incrementa el
        ID y crea una entrada en el diccionario de entidades y en el de
        metadatos. El diccionario de metadatos se comparte entre todas las
        colecciones derivadas, y se puede usar para almacenar información
        adicional sobre las entidades.

        Todo argumento pasado aparte de la entidad a añadir, se almacena como
        metadato de la entidad.

        Devuelve el ID interno de la entidad añadida.

        """
        iid = self._iid[0]
        self._entities[iid] = entity
        _copy = deepcopy(BASE_META)
        _copy.update(meta)
        self._meta[iid] = _copy
        self._iid[0] += 1
        return iid

    def _subset(self, entities: list[int], iid: list[int]) -> Collection:
        """Crea una nueva colección derivada de esta.

        Recibe el listado con los IDs internos de cada entidad, y el puntero
        al ID interno de la colección. Copia las entidades adecuadas junto con
        sus metadatos.

        Devuelve una nueva colección con la misma base y dichos datos.

        """
        subset = self.__class__(self._base, pkeys=self.pkeys)
        subset._entities = {iid: self._entities[iid] for iid in entities}
        subset._meta = self._meta
        subset._iid = iid
        return subset

    @property
    def _active(self) -> list[tuple[int, CollectionEntity]]:
        """Devuelve una lista de tuplas (iid, entity) de las entidades activas."""
        return [
            (iid, entity)
            for iid, entity in self._entities.items()
            if self._meta[iid]["status"] == "active"
        ]

    @property
    def _changed(self) -> list[tuple[int, CollectionEntity, list[str]]]:
        """Devuelve una lista de tuplas (iid, entity, changes) de las entidades modificadas."""
        return [
            (iid, entity, self._meta[iid]["changes"])
            for iid, entity in self._entities.items()
            if self._meta[iid]["changes"]
        ]

    @property
    def _deleted(self) -> list[tuple[int, CollectionEntity]]:
        """Devuelve una lista de tuplas (iid, entity) de las entidades eliminadas."""
        return [
            (iid, entity)
            for iid, entity in self._entities.items()
            if self._meta[iid]["status"] == "deleted"
        ]

    @property
    def _new(self) -> list[tuple[int, CollectionEntity]]:
        """Devuelve una lista de tuplas (iid, entity) de las entidades nuevas."""
        return [
            (iid, entity)
            for iid, entity in self._entities.items()
            if self._meta[iid]["source"] == "new"
        ]

    # Métodos de comprobación
    def empty(self) -> bool:
        """Devuelve True si la colección está vacía."""
        return not bool(self._active)

    def __iter__(self) -> Collection:
        """Itera sobre las entidades activas de la colección.

        No devuelve el elemento de por sí, sino otra colección de un solo
        elemento. De esta forma, si se modifican atributos, se siguen
        monitorizando por la clase. Si se quiere acceder al elemento, se puede
        usar el atributo 'entity'.

        """
        for iid, _ in self._active:
            yield self._subset([iid], self._iid)

    def sort(self, *args: str, reverse: bool = False) -> Collection:
        """Ordena las entidades de la colección.

        Se pueden pasar varios atributos para ordenar por ellos, en orden de
        prioridad.

        Si se indica 'reverse=True', se invierte el orden de ordenación.

        Itera por la colección ordenadamente.

        """
        key = lambda x: [getattr(x[1], attr) for attr in args]
        for iid, _ in sorted(self._active, key=key, reverse=reverse):
            yield self._subset([iid], self._iid)

    def __len__(self) -> int:
        """Devuelve la cantidad de entidades activas de la colección."""
        return len(self._active)

    # Métodos de manipulación
    def new(self, *args: Any, **kwargs: Any) -> Collection:
        """Crea una nueva entidad, usando el constructor original, y la añade
        a la colección.

        No se realiza ninguna comprobación sobre la validez de los datos.
        Cualquier error que se produzca será lanzado por el constructor
        y no por este método.

        Devuelve una colección de un solo elemento con la nueva entidad.

        """
        entity = self._base(*args, **kwargs)
        iid = self._append(entity, source="new")
        return self._subset([iid], self._iid)

    def add(self, entity: CollectionEntity) -> Collection:
        """Añade una entidad a la colección.

        'entity' debe ser una instancia de la clase base de la colección. No
        se comprueba si la entidad ya existe en la colección.

        Devuelve una colección de un solo elemento con la nueva entidad.

        """
        if not isinstance(entity, self._base):
            raise TypeError(f"La entidad debe ser de tipo {self._base!r}")
        iid = self._append(entity, source="add")
        return self._subset([iid], self._iid)

    def update(
        self, *args: object | Callable[[Any], Any], **kwargs: object | Callable[[Any], Any]
    ) -> None:
        """Actualiza todas las entidades de esta colección.

        Normalmente, este método se llama indicando los atributos a modificar
        mediante **kwargs, siendo cada clave el nombre del atributo y cada
        valor el nuevo valor del atributo. Si en vez de ello se usan *args,
        estos se aplicarán, en orden, sobre los atributos que hayan sido
        definidos como claves primarias. Si no hay claves primarias definidas,
        se ignorarán. Si hay más valores que claves primarias, se ignorarán
        los sobrantes.

        Nota: Si se usan *args pero luego se especifican atributos mediante
        **kwargs, se ignorarán estos últimos.

        El nuevo valor puede ser cualquier valor válido para el atributo, o,
        en caso de ser una función, el valor devuelto por la función al pasarle
        el actual valor de dicho atributo como argumento.

        """
        if args:
            for pkey, arg in zip(self.pkeys, args):
                kwargs[pkey] = arg
        for attr, value in kwargs.items():
            for iid, entity in self._active:
                tvalue = value(getattr(entity, attr)) if callable(value) else value
                if getattr(entity, attr) != tvalue:
                    self._meta[iid]["changes"].append(attr)
                    setattr(entity, attr, tvalue)

    def __setattr__(self, attr: str, value: Any) -> None:
        """Adaptación para que los atributos no propios de 'Collection' se
        apliquen a las entidades de la colección.

        Cuando el atributo no pertenece a 'Collection', se trata de aplicar
        a todas las entidades (como un 'update').

        Si la colección está vacía (de elementos activos), o si el atributo
        no pertenece a las entidades, se lanza una excepción.

        """
        if attr in self.__dict__:
            super().__setattr__(attr, value)
        else:
            if self.empty():
                raise AttributeError(
                    f"'{attr!r}' no es un atributo de 'Collection' y la colección está vacía."
                )
            aux = next(iter(self._active))[1]
            if hasattr(aux, attr):
                self.update(**{attr: value})
            else:
                raise AttributeError(
                    f"{attr!r} no es un atributo de 'Collection' ni de '{self._base.__name__}'"
                )

    def delete(self) -> None:
        """Elimina todas las entidades de esta colección."""
        for iid, _ in self._active:
            self._meta[iid]["status"] = "deleted"

    # Métodos de consulta, filtrado y búsqueda
    def search(
        self, *args: object | Callable[[CollectionEntity], bool], **kwargs: Any
    ) -> Collection | None:
        """Busca entidades de acuerdo a las condiciones indicadas.

        La forma estándar de usar este método es indicando los atributos a
        buscar mediante **kwargs, siendo cada clave el nombre del atributo y
        cada valor el valor a buscar. Alternativamente, se pueden pasar
        mediante *args funciones que reciban una entidad y devuelvan un valor
        booleano en función de si la entidad cumple o no las condiciones. Todas
        las condiciones se unen mediante un AND lógico.

        Si *args recibe valores que no son funciones, estas se asignarán, en
        orden, a los atributos que hayan sido definidos como claves primarias.
        Si no hay claves primarias definidas, se ignorarán. Si hay más valores
        que claves primarias, se ignorarán los sobrantes. Tener en cuenta que
        si luego estas claves se vuelven a especificar mediante **kwargs, se
        ignorarán estos últimos.

        Si se usa tanto *args para valores a asignar a las claves primarias,
        como con funciones, NO pueden aparecer valores que no sean funciones
        después de la primera función.

        Devuelve una nueva colección derivada sólo con las entidades que
        cumplen las condiciones, o None, si la colección está vacía.

        """
        # Dividiendo argumentos posicionales en funciones y valores
        positional = []
        filters = []
        _lock_args = False
        for arg in args:
            if callable(arg):
                _lock_args = True
                filters.append(arg)
            elif _lock_args:
                raise TypeError(
                    "Los argumentos de valores para claves primarias "
                    "no pueden aparecer después de argumentos de funciones de filtrado."
                )
            else:
                positional.append(arg)
        # Si hay posicionales, llamamos a este mismo método asignando, en orden
        # los valores a las claves primarias, hasta que alguna ejecución no
        # devuelva None.
        if positional:
            for keys in windowed(self.pkeys, len(positional)):
                extra = {k: v for k, v in zip(keys, positional)}
                res = self.search(*filters, **kwargs, **extra)
                if res:
                    return res
        else:
            for attr, value in kwargs.items():
                filters.append(lambda entity: getattr(entity, attr) == value)
            entities = [iid for iid, entity in self._active if all(f(entity) for f in filters)]
            if entities:
                return self._subset(entities, self._iid)
        return None

    def get(
        self, *args: object | Callable[[CollectionEntity], bool], **kwargs: Any
    ) -> Collection | None:
        """Obtiene una única entidad de acuerdo a las condiciones indicadas.

        La forma estándar de usar este método es indicando los atributos a
        buscar mediante **kwargs, siendo cada clave el nombre del atributo y
        cada valor el valor a buscar. Alternativamente, se pueden pasar
        mediante *args funciones que reciban una entidad y devuelvan un valor
        booleano en función de si la entidad cumple o no las condiciones. Todas
        las condiciones se unen mediante un AND lógico.

        Si *args recibe valores que no son funciones, estas se asignarán, en
        orden, a los atributos que hayan sido definidos como claves primarias.
        Si no hay claves primarias definidas, se ignorarán. Si hay más valores
        que claves primarias, se ignorarán los sobrantes. Tener en cuenta que
        si luego estas claves se vuelven a especificar mediante **kwargs, se
        ignorarán estos últimos.

        Si se usa tanto *args para valores a asignar a las claves primarias,
        como con funciones, NO pueden aparecer valores que no sean funciones
        después de la primera función.

        Devuelve una colección de un solo elemento con la entidad que cumple
        las condiciones, o None, si la colección está vacía. En caso de que
        varias entidades cumplan las condiciones, se devuelve la primera.

        """
        c = self.search(*args, **kwargs)
        if c:
            iid = next(iter(c._active))[0]
            return self._subset([iid], self._iid)
        return None

    def __getitem__(self, key: Any) -> Collection | None:
        """Syntax sugar para 'get' usando las claves primarias.

        Si no hay claves primarias definidas, se lanza una excepción.

        """
        if not self.pkeys:
            raise TypeError("No hay claves primarias definidas.")
        if isinstance(key, (list, tuple)):
            self.get(*key)
        else:
            return self.get(key)

    def __getattr__(self, attr: str) -> Any:
        """Adaptación para que los atributos no propios de 'Collection' se
        apliquen a las entidades de la colección.

        Cuando el atributo no pertenece a 'Collection' y en la colección sólo
        hay un elemento, se devuelve el valor del atributo de dicha entidad.

        Si la colección está vacía (de elementos activos), o si el atributo
        no pertenece a las entidades, se lanza una excepción.

        """
        if self.empty():
            raise AttributeError(
                f"{attr!r} no es un atributo de 'Collection' y la colección está vacía."
            )
        elif len(self) > 1:
            raise AttributeError(
                f"{attr!r} no es un atributo de 'Collection' y la colección tiene más de un elemento."
            )
        else:
            entity = self.entity
            try:
                return getattr(entity, attr)
            except AttributeError:
                raise AttributeError(
                    f"{attr!r} no es un atributo de 'Collection' ni de '{self._base.__name__}'"
                ) from None

    # Métodos de representación
    def show(self) -> None:
        """Muestra los datos de la colección directamente por pantalla."""
        entities = [i[1] for i in self._active]
        try:
            for entity in sorted(entities):
                print(entity)
        except:
            for entity in entities:
                print(entity)

    def __repr__(self) -> str:
        """Representación de la colección."""
        return f"<Collection {self._base.__name__} ({len(self)})>"

    def __str__(self) -> str:
        """Representación de la colección."""
        if len(self) == 1:
            return str(self.entity)
        return repr(self)
