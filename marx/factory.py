# Python 3.10.11
# Creado: 28/06/2024
"""Clase auxiliar para gestionar listas de objetos industrializados"""

from __future__ import annotations

from typing import Any, Callable, Generic, TypeVar

FactoryItem = TypeVar("FactoryItem")


class Factory(Generic[FactoryItem]):
    """Presenta listas de objetos industrializados

    Un objeto es industrializado cuando se puede crear a partir de parámetros
    concretos, y se quiere mantener un registro de su origen y cambios.

    Este gestor permite crear, añadir, modificar, eliminar, buscar, filtrar,
    ordenar y extraer objetos de una misma clase. También posee un registro de
    cambios público.

    Todas las operaciones que devuelvan objetos, devolverán un subconjunto de
    la factoría original. Para extraer el objeto original, se debe usar el
    método 'pull' o 'pullone'.

    El constructor requiere la clase de los objetos a gestionar.

    """

    def __init__(self, base: type[FactoryItem]) -> None:
        # Como sobrescribimos __setattr__, inicializamos con super()
        super().__setattr__("_base", base)
        super().__setattr__("_items", [])

    # Métodos públicos
    def new(self, *args: Any, **kwargs: Any) -> Factory:
        """Crea un nuevo objeto mediante el constructor de la clase base
        y los argumentos proporcionados.

        """
        raise NotImplementedError

    def push(self, item: FactoryItem) -> None:
        """Añade un objeto a la factoría

        Si el objeto no es de la clase base, se lanzará una excepción.

        """
        raise NotImplementedError

    def pull(self) -> list[FactoryItem]:
        """Extrae todos los objetos de la factoría, en forma de lista

        Si el objeto no está en la factoría, devuelve una lista vacía.

        """
        raise NotImplementedError

    def pullone(self) -> FactoryItem | None:
        """Extrae un objeto de la factoría, el primero de la lista

        Si el objeto no está en la factoría, devuelve None.

        """
        raise NotImplementedError

    def update(self, **kwargs: Any) -> None:
        """Actualiza los atributos de todos los objetos en la factoría

        Si el valor de un parámetro es una función, el nuevo valor asignado
        será el resultante de aplicar dicha función al valor actual.

        En caso de incluir parámetros no existentes, se ignorarán.

        """
        raise NotImplementedError

    def delete(self) -> None:
        """Elimina todos los objetos de la factoría"""
        raise NotImplementedError

    def get(self, *args: Callable[[FactoryItem], bool], **kwargs: Any) -> Factory:
        """Filtra y devuelve un subconjunto de la factoría en función de los
        argumentos proporcionados.

        Los argumentos pueden ser:

        *args: Funciones que reciben como parámetro un objeto de la factoría y
            devuelven True si se debe incluir en el subconjunto, y False en
            caso contrario.

        **kwargs: Parámetros que deben coincidir con los atributos de los
            objetos de la factoría. Si se indican parámetros inexistentes,
            se ignorarán.

        En caso de incluir ambos tipos de argumentos, primero aplicarán las
        funciones.

        """
        raise NotImplementedError

    def sort(self, *args: str, reverse: bool = False) -> Factory:
        """Ordena los objetos de la factoría en función de los atributos
        proporcionados. Si se indica 'reverse=True', se invertirá el orden.

        """
        raise NotImplementedError
