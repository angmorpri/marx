# Python 3.10.11
# Creado: 24/02/2024
"""Gestión automatizada de distribuciones de capital entre cuentas.

Una distribución se representa con un origen y uno o varios destinos, cada uno
de los cuales compuesto de una cantidad fija que tiene que ser distribuida, o
un porcentaje de la cantidad total a distribuir.

Se definen las clases 'DistrSource' y 'DistrSink' para representar,
respectivamente, el origen y los destinos de la distribución. A su vez, la
clase 'Distribution' actúa como interfaz para configurar y llevar a cabo la
distribución.

Se pueden utilizar archivos de configuración INI para definir distribuciones
complejas.

"""
from __future__ import annotations

import random
import string
from datetime import datetime

from marx.model import Account, Category, MarxDataStruct
from marx.util import Collection, parse_nested_cfg


Counterpart = str


class DistrSource:
    """Fuente del capital a distribuir.

    Se compone de un origen ('target'), que puede ser una cuenta o un pagador;
    y de una cantidad, que a su vez puede indicarse como un valor absoluto
    ('amount') o como un porcentaje del total disponible en la cuenta
    ('ratio'). En este último caso, el origen debe ser una cuenta.

    Para definir el origen, se debe modificar el atributo 'target'. Éste
    admite, para cuentas, objetos de la clase 'Account' o bien el nombre de la
    cuenta precedido por '@'. En cualquier otro caso, se considerará que se
    indica un pagador.

    De la misma forma, la cantidad a distribuir se puede definir o de forma
    absoluta mediante 'amount' o de forma relativa mediante 'ratio', teniendo
    en cuenta que definir uno inhabilita el otro. En el caso de 'ratio', se
    admiten tanto valores porcentuales entre [0, 1] como entre [0, 100].

    Antes de crear objetos de esta clase, se debe indicar la colección de
    cuentas que se está usando mediante el atributo de clase 'ACCOUNTS'.

    """

    ACCOUNTS: Collection[Account]

    def __init__(self):
        self._target = None
        self._amount = 0.0
        self._ratio = 0.0

    @property
    def target(self) -> Account | str | None:
        return self._target

    @target.setter
    def target(self, target: Account | str) -> None:
        if self.ACCOUNTS is None:
            raise ValueError(
                "No se ha configurado la colección de cuentas a usar para la distribución."
            )
        if isinstance(target, Account):
            self._target = target
        elif isinstance(target, str) and target.startswith("@"):
            self._target = self.ACCOUNTS.get(target[1:]).entity
            if not self._target:
                raise ValueError(f"La cuenta con nombre '{target[1:]}' no existe.")
        else:
            raise ValueError("El origen debe ser una cuenta o un pagador.")

    @property
    def amount(self) -> float | None:
        return self._amount

    @amount.setter
    def amount(self, amount: float) -> None:
        if self._target is None:
            raise ValueError("Debe definirse un origen antes de una cantidad o ratio.")
        self._amount = amount

    @property
    def ratio(self) -> float | None:
        return self._ratio

    @ratio.setter
    def ratio(self, ratio: float) -> None:
        if self._target is None:
            raise ValueError("Debe definirse un origen antes de una cantidad o ratio.")
        if isinstance(self._target, Counterpart):
            raise ValueError("No se puede aplicar un ratio a un pagador.")
        if not 0 <= ratio <= 100:
            raise ValueError(
                "El ratio debe ser un valor porcentual expresado entre [0, 1] o [0, 100]."
            )
        self._ratio = ratio / 100 if ratio > 1 else ratio

    def __str__(self) -> str:
        return f"Source({self.target}, {self.amount:.2f} | {self.ratio:.2%})"


class DistrSink(DistrSource):
    """Sumidero de capital a distribuir.

    Se compone de un destino ('target'), que puede ser una cuenta o una
    contraparte; y de una cantidad, que puede ser un valor absoluto ('amount')
    o un porcentaje del total a distribuir ('ratio').

    Además, define los siguientes atributos que serán necesarios para generar
    un nuevo evento cuando se lleve a cabo el reparto:
    - 'category': categoría del evento. Puede ser un objeto Category o bien
        una cadena indicando el código o el nombre completo de ésta.
    - 'concept': concepto del evento.
    - 'details': opcional, detalles adicionales del evento.

    El constructor recibe todos los parámetros en el orden 'target',
    'category', 'concept', 'details', y, luego, sólo uno entre 'amount' y
    'ratio'. Si se reciben los dos o ninguno, se lanzará un ValueError.

    Finalmente, se proporciona también un parámetro 'sid' opcional, que actúa
    como identificador unívoco del sumidero. Si no se proporciona, se generará
    automáticamente.

    Antes de crear objetos de esta clase, se debe indicar la colección de
    cuentas que se está usando mediante el atributo de clase 'ACCOUNTS', y la
    de categorías mediante 'CATEGORIES'.

    """

    CATEGORIES = Collection[Category]

    def __init__(
        self,
        target: Account | str,
        category: Category | str,
        concept: str,
        details: str = "",
        amount: float | None = None,
        ratio: float | None = None,
        *,
        sid: str | None = None,
    ):
        super().__init__()
        self.sid = sid or "".join(random.choices(string.ascii_letters, k=8))
        self.target = target
        self.category = category
        self.concept = concept
        self.details = details

        # Cantidades o ratios
        if amount is None and ratio is None:
            raise ValueError("Un sumidero necesita especificar cantidad o ratio a recibir.")
        elif amount is not None and ratio is not None:
            raise ValueError("Un sumidero sólo puede definir cantidad o ratio, pero no ambas.")
        self.amount = amount or 0.0
        self.ratio = ratio or 0.0

    @property
    def category(self) -> Category:
        return self._category

    @category.setter
    def category(self, category: Category | str) -> None:
        if self.CATEGORIES is None:
            raise ValueError(
                "No se ha configurado la colección de categorías a usar para la distribución."
            )
        if isinstance(category, Category):
            self._category = category
        elif isinstance(category, str):
            self._category = self.CATEGORIES.get(category).entity
            if not self._category:
                raise ValueError(f"La categoría con código o nombre '{category}' no existe.")
        else:
            raise ValueError("La categoría debe ser un objeto Category o una cadena.")

    def __str__(self) -> str:
        return (
            f"Sink({self.target}, {self.amount:.2f} | {self.ratio:.2%},"
            f" [{self.category.code}, {self.concept!r}, {self.details!r}])"
        )


class Distribution:
    """Interfaz para gestión automatizada de distribuciones de capital.

    Presenta los mecanismos para:
    1. Configurar un origen de la distribución.
    2. Crear y añadir sumideros para la distribución.
    3. Preparar la distribución, comprobando que es posible.
    4. Llevar a cabo la distribución, generando los eventos necesarios.

    Para configurar orígenes y sumideros se proporcionan los atributos 'source'
    y 'sinks', respectivamente. El primero admite una cuenta o un pagador, y
    crea, a partir de éste, un objeto de la clase DistrSource. El segundo es
    una colección de sumideros inicialmente vacía, al que se pueden añadir
    nuevos sumideros mediante el método 'new' o 'add'.

    Para preparar la distribución, se debe llamar al método 'prepare'. Este
    calcula si la distribución es posible. Para ejecutarla, generando los
    eventos necesarios, se debe llamar al método 'run'.

    El constructor requiere como único argumento una estructura de datos de
    Marx ya cargada. Alternativamente, se proporciona el método de clase
    'from_cfg', que, además de la estructura, recibe la ruta a un archivo de
    definición para una distribución, cargándola inmediatamente.

    """

    def __init__(self, data: MarxDataStruct) -> None:
        self._data = data
        DistrSource.ACCOUNTS = self._data.accounts
        DistrSink.ACCOUNTS = self._data.accounts
        DistrSink.CATEGORIES = self._data.categories

        self._source = DistrSource()
        self._sinks = Collection(DistrSink, pkeys=["sid"])
        self._events = []  # Lista de eventos generados

        self.__prepared__ = False

    @classmethod
    def from_cfg(cls, data: MarxDataStruct, cfg_path: str) -> Distribution:
        """Carga una distribución a partir de un archivo de configuración.

        En el archivo de configuración se deben especificar, al menos, los
        siguientes parámetros:
        - fuente ('source'), con el origen ('target') y la cantidad ('amount' o
            'ratio').
        - sumideros (como subsecciones de 'sinks'), con el destino ('target'),
            la cantidad ('amount' o 'ratio'), la categoría ('category') y,
            opcionalmente, el concepto ('concept') y los detalles ('details').

        Se debe proporcionar también una relación de datos de Marx 'data'.

        """
        distr = cls(data)
        cfg = parse_nested_cfg(cfg_path)
        # Fuente
        if "source" not in cfg:
            raise ValueError("No se ha especificado la fuente de capital.")
        if "target" not in cfg["source"]:
            raise ValueError("No se ha especificado el origen de la fuente de capital.")
        if "amount" not in cfg["source"] and "ratio" not in cfg["source"]:
            raise ValueError("No se ha especificado la cantidad a distribuir.")
        distr.source = cfg["source"]["target"]
        if "amount" in cfg["source"]:
            distr.source.amount = cfg["source"]["amount"]
        if "ratio" in cfg["source"]:
            distr.source.ratio = cfg["source"]["ratio"]
        # Sumideros
        if "sinks" not in cfg:
            raise ValueError("No se han especificado sumideros.")
        for key, sink in cfg["sinks"].items():
            if key == "__defaults__":
                continue
            if "target" not in sink:
                raise ValueError(f"No se ha especificado el destino del sumidero {key}.")
            if "amount" not in sink and "ratio" not in sink:
                raise ValueError(f"No se ha especificado la cantidad del sumidero {key}.")
            if "category" not in sink:
                raise ValueError(f"No se ha especificado la categoría del sumidero {key}.")
            if "ratio" in sink:
                sink["ratio"] = sink["ratio"]
            distr.sinks.new(sid=key, **sink)
        return distr

    @property
    def source(self) -> DistrSource:
        return self._source

    @source.setter
    def source(self, target: Account | str) -> None:
        self._source.target = target

    @property
    def sinks(self) -> Collection[DistrSink]:
        return self._sinks

    @property
    def events(self) -> list:
        return self._events

    def prepare(self, *, verbose: bool = False) -> None:
        """Prepara la distribución.

        Comprueba si es posible ejecutarla según una serie de criterios en
        función de si se reparte desde una cuenta o un pagador, como ratio o
        como cantidad absoluta; y si los sumideros son en ratio o en cantidad
        absoluta.

        Si 'verbose' es True, se mostrará el resultado por pantalla.

        """
        if self.__prepared__:
            return

        # Orígenes y destinos no nulos ni contrapartes
        if self._source.target is None:
            raise ValueError("No se ha definido la fuente de capital.")
        if isinstance(self._source.target, Counterpart) and any(
            isinstance(sink.target, Counterpart) for sink in self._sinks
        ):
            raise ValueError(
                "Si el origen es una contraparte, ningún sumidero puede ser contraparte."
            )

        # En función del tipo de origen, se calcula la cantidad a distribuir
        if isinstance(self.source.target, Account):
            # Se calcula el saldo real de la cuenta
            real_amount = 0.0
            for event in self._data.events.search(orig=self.source.target, status="closed"):
                real_amount -= event.amount
            for event in self._data.events.search(dest=self.source.target, status="closed"):
                real_amount += event.amount
            if real_amount <= 0.0:
                raise ValueError("La cuenta origen no tiene saldo suficiente para repartir.")
            # Si se ha definido una cantidad, se calcula el ratio
            if self.source.amount != 0.0:
                self.source.ratio = self.source.amount / real_amount
            # Si se ha definido un ratio, se calcula la cantidad
            elif self.source.ratio != 0.0:
                self.source.amount = real_amount * self.source.ratio
            # Se comprueba que la cantidad a distribuir es suficiente
            if self.source.amount > real_amount:
                raise ValueError(
                    f"La cantidad a distribuir es superior a la cantidad real de la cuenta"
                    f" ({self.source.amount} < {real_amount})."
                )
        else:
            # Sólo se ha podido definir una cantidad, así que el ratio será 1
            self.source.ratio = 1.0

        # Se comprueba que la cantidad a distribuir es suficiente para los
        # sumideros configurados
        sinks_total_amount = sum(sink.amount for sink in self._sinks)
        sinks_total_ratio = sum(sink.ratio for sink in self._sinks)
        if sinks_total_ratio > 1.0:
            raise ValueError("La suma de los ratios de los sumideros no puede superar el 100%.")
        if self.source.amount < sinks_total_amount:
            raise ValueError(
                f"La cantidad a distribuir es menor a la cantidad asignada a los sumideros"
                f" ({self.source.amount} < {sinks_total_amount})."
            )
        if sinks_total_ratio != 0.0 and (self.source.amount - sinks_total_amount) <= 0.01:
            raise ValueError("No se pueden aplicar ratios de sumideros a una cantidad nula.")

        # Se ajustan las cantidades y ratios de cada sumidero:
        left = self.source.amount - sinks_total_amount
        for sink in self.sinks:
            if sink.amount != 0.0:
                sink.ratio = sink.amount / self.source.amount
            elif sink.ratio != 0.0:
                sink.amount = sink.ratio * left

        # Resumen
        if verbose:
            print(
                f"De {self.source.target} se reparten {self.source.amount:.2f} € ({self.source.ratio:.2%})"
            )
            pl = []
            for sink in self.sinks:
                key = f" - A {sink.target} ({sink.category.code}, {sink.concept}): "
                value = f"{sink.amount:.2f} ({sink.ratio:.2%})"
                pl.append((key, value))
            padl = max(len(key) for key, _ in pl) + 1
            padr = max(len(value) for _, value in pl) + 1
            for key, value in pl:
                print(f"{key:<{padl}}{value:>{padr}}")
            left = self.source.amount - sum(sink.amount for sink in self.sinks)
            print(f"Quedan {left:.2f} € sin asignar.")

        self.__prepared__ = True

    def run(self, date: datetime | str | None = None) -> None:
        """Ejecuta la distribución.

        Se puede proveer una fecha para los eventos generados. Si no se hace,
        se usará la fecha actual. El formato puede ser o bien un objeto
        'datetime', o bien una cadena en formato 'YYYY-MM-DD'.

        Antes de ejecutar la distribución, se comprobará que ésta ha sido
        preparada previamente, y en caso contrario, la preparará.

        """
        if not self.__prepared__:
            self.prepare()

        date = date or datetime.now()
        if isinstance(date, str):
            date = datetime.strptime(date, "%Y-%m-%d")

        self._events = []
        for sink in self._sinks:
            event = self._data.events.new(
                id=-1,
                date=date,
                amount=sink.amount,
                category=sink.category,
                orig=self.source.target,
                dest=sink.target,
                concept=sink.concept,
                details=sink.details,
            )
            self._events.append(event)

    def __str__(self) -> str:
        return f"Distribution({self._source}, {len(self._sinks)} sumideros)"

    def show(self) -> None:
        """Muestra la distribución por pantalla de una forma organizada."""
        print(
            f"Se distribuyen {self.source.amount:.2f}€ o el {self.source.ratio:.2%} de {self.source.target} a:"
        )
        for sink in self.sinks:
            print(f"  - {sink.target}: {sink.amount:.2f}€ o el {sink.ratio:.2%}")
