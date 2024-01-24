# Python 3.10.11
# Creado: 24/01/2024
"""Clase para representar una colección de datos.

Una colección de datos permite almacenar un conjunto de datos de un mismo tipo,
además de crearlos, modificarlos y eliminarlos individual o masivamente desde
la propia interfaz de la colección. También proporciona mecanismos de búsqueda
y filtrado.

"""

from typing import Any, Callable

CollectionEntity = object


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
        self._base = base
        self._entities = []

        self.pkeys = pkeys or []  # Público, se puede modificar

    # Métodos de manipulación
    def new(self, *args: Any, **kwargs: Any) -> CollectionEntity:
        """Crea una nueva entidad, usando el constructor original, y la añade
        a la colección.

        No se realiza ninguna comprobación sobre la validez de los datos.
        Cualquier error que se produzca será lanzado por el constructor
        y no por este método.

        Devuelve la nueva entidad creada.

        """
        entity = self._base(*args, **kwargs)
        self.add(entity)
        return entity

    def add(self, entity: CollectionEntity) -> None:
        """Añade una entidad a la colección.

        'entity' debe ser una instancia de la clase base de la colección. No
        se comprueba si la entidad ya existe en la colección.

        """
        self._entities.append(entity)

    def update(self, *args: Any, **kwargs: Any) -> None:
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

        """
        if args:
            for pkey, arg in zip(self.pkeys, args):
                kwargs[pkey] = arg
        for attr, value in kwargs.items():
            for entity in self._entities:
                setattr(entity, attr, value)
