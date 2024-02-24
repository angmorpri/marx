# Python 3.10.11
# Creado: 24/02/2024
"""Clase para automatizar distribuciones de capital entre cuentas y 
contrapartes.

Define la clase Distribution, que permite configurar una fuente y uno o varios
sumideros de capital, junto con la cantidad a distribuir, en formato absoluto o
relativo.

"""

import random
import string
from datetime import datetime

from marx.model import Account, Category, Collection, MarxAdapter


class DistrSource:
    """Fuente de capital a distribuir.

    Está formada por un origen ('target'), que puede ser una cuenta o un
    pagador; y una cantidad ('amount'/'ratio'), que indica la cantidad a
    distribuir.

    Para definir 'target' como una cuenta, se puede pasar directamente un
    objeto de la clase Account; o, alternativamente, un string con el nombre
    de la cuenta precedido por el símbolo '@' (ej. '@cuenta').

    La cantidad puede ser definida de forma absoluta o relativa. El primer caso
    es válido tanto si el origen es una cuenta como si es un pagador: sólo se
    usará para garantizar que no se exceda dicha cantidad a la hora de repartir
    a los sumideros. El segundo caso sólo es válido si el origen es una cuenta,
    y determinará qué porcentaje de la cantidad acumulada en ésta se reparte.
    Si la cantidad es None o no se puede aplicar, se asumirá que es el total
    acumulado en la cuenta.

    El constructor no recibe parámetros. Antes de usar objetos de la clase, se
    debe configurar a nivel de clase la colección de cuentas que usar, mediante
    el atributo de clase 'ACCOUNTS'.

    """

    ACCOUNTS: Collection[Account]

    def __init__(self):
        self._target = None
        self._amount = None
        self._ratio = None

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
    def amount(self, amount: float | None) -> None:
        self._amount = amount

    @property
    def ratio(self) -> float | None:
        return self._ratio

    @ratio.setter
    def ratio(self, ratio: float | None) -> None:
        if ratio is None:
            self._ratio = None
        elif not 0 <= ratio <= 100:
            raise ValueError(
                "El ratio debe ser un valor porcentual expresado entre [0, 1] o [0, 100]."
            )
        if ratio > 1:
            ratio /= 100
        self._ratio = ratio

    def __str__(self) -> str:
        return f"Source({self._target}, {self._amount}, {self._ratio})"


class DistrSink(DistrSource):
    """Sumidero de capital a distribuir.

    Está formado de un destino ('target') y una cantidad ('amount'/'ratio'),
    que se rigen por las mismas reglas que en DistrSource, con la única
    diferencia de que ahora, si 'target' es una contraparte, sí acepta un ratio
    como cantidad.

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

    Antes de usar objetos de la clase, se debe configurar a nivel de clase la
    colección de cuentas que usar, mediante el atributo de clase 'ACCOUNTS'; y
    la colección de categorías que usar, mediante el atributo de clase
    'CATEGORIES'.

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
        # Inicializados en DistrSource
        self.target = target
        if amount is not None and ratio is not None:
            raise ValueError("Sólo se puede definir una cantidad, no ambas.")
        if amount is None and ratio is None:
            raise ValueError("Se debe definir una cantidad.")
        if amount is not None:
            self._amount = amount
        else:
            self.ratio = ratio
        # Nuevos atributos
        self.concept = concept
        self.details = details
        self._category = None
        self.category = category
        # Identificador
        sid = sid or "".join(random.choices(string.ascii_letters, k=8))

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
        if self._amount is not None:
            return f"Sink({self._target}, {self._amount}, {self._category}, {self.concept}, {self.details})"
        else:
            return f"Sink({self._target}, {self._ratio}, {self._category}, {self.concept}, {self.details})"


class Distribution:
    """Distribución de capital entre cuentas y/o contrapartes.

    Esta clase presenta una interfaz en la que se pueden configurar una fuente
    y uno o varios sumideros de capital, junto con la cantidad a distribuir. A
    continuación, permite tanto comprobar que dicha distribución es posible, y
    en caso afirmativo, llevarla a cabo, generando tantos nuevos eventos como
    sean necesarios para reflejar la operación.

    Se pueden configurar los siguientes atributos:
    - 'source': fuente de capital a distribuir. Debe ser una cuenta o un
        pagador. En el primer caso, ésta puede representarse bien con objeto
        de la clase Account o bien con una cadena que indique el nombre de la
        cuenta precedido por el símbolo '@'.
    - 'source.amount' o 'source.ratio': cantidad a distribuir. Si se define
        'amount', se usará como cantidad absoluta; si se define 'ratio', se
        usará como cantidad relativa.
    - 'sinks': colección de sumideros. Se pueden añadir nuevos mediante el
        método 'new', y también ubicar y modificar los ya existentes mediante
        'get', 'update' y 'delete'.

    Y se proporcionan los siguientes métodos:
    - 'check': comprueba si la distribución es posible. Con el parámetro 'show'
        se puede indicar si se quiere mostrar el resultado por pantalla.
    - 'run': lleva a cabo la distribución. Si la distribución no es posible,
        se lanzará un ValueError. Si se proporciona una fecha, se usará esa como
        fecha de los eventos generados; si no, se usará la fecha actual.

    El constructor requiere como parámetro un MarxAdapter para poder acceder a
    la base de datos.

    """

    def __init__(self, adapter: MarxAdapter) -> None:
        self._adapter = adapter
        self._adapter.load()
        DistrSource.ACCOUNTS = self._adapter.suite.accounts
        DistrSink.ACCOUNTS = self._adapter.suite.accounts
        DistrSink.CATEGORIES = self._adapter.suite.categories

        self._source = DistrSource()
        self._sinks = Collection(DistrSink, pkeys=["sid"])

    @property
    def source(self) -> DistrSource:
        return self._source

    @source.setter
    def source(self, target: Account | str) -> None:
        self._source.target = target

    @property
    def sinks(self) -> Collection[DistrSink]:
        return self._sinks

    def check(self, *, show: bool = False) -> bool:
        """Comprueba si la distribución es posible.

        Si 'show' es True, se mostrará el resultado por pantalla.

        """
        # Orígenes y destinos
        if self._source.target is None:
            raise ValueError("No se ha definido la fuente de capital.")
        if isinstance(self._source.target, str) and any(
            isinstance(sink.target, str) for sink in self._sinks
        ):
            raise ValueError("No se pueden usar contrapartes como fuente y destino a la vez.")

        # Cantidad a distribuir
        base_total = None
        to_distr = 0
        if isinstance(self._source.target, Account):
            to_distr = 0
            for event in self._adapter.suite.events.search(
                orig=self._source.target, status="closed"
            ):
                to_distr -= event.amount
            for event in self._adapter.suite.events.search(
                dest=self._source.target, status="closed"
            ):
                to_distr += event.amount
            base_total = to_distr
            if self._source.amount is not None:
                to_distr = min(to_distr, self._source.amount)
            elif self._source.ratio is not None:
                to_distr *= self._source.ratio

        # Sumideros
        balance_check = to_distr
        for sink in self._sinks:
            if sink.ratio is not None:
                if to_distr == 0:
                    raise ValueError("No se puede aplicar un ratio a una cantidad nula.")
                sink._amount = sink.ratio * to_distr
            balance_check -= sink.amount
            if balance_check < 0:
                raise ValueError("La cantidad a distribuir es insuficiente.")

        # Resumen
        if show:
            to_distr = sum(sink.amount for sink in self._sinks)
            extra = ""
            if base_total:
                extra = f" ({to_distr/base_total:.2%} del total)"
            print(f"De {self._source.target} se reparten {to_distr:.2f}{extra}")
            print("A:")
            for sink in self._sinks:
                print(f"    {sink.target}: {sink.amount:.2f} ({sink.amount/to_distr:.2%})")
            print()
        return True

    def run(self, date: datetime | str | None = None) -> None:
        """Ejecuta la distribución.

        Se puede proveer una fecha para los eventos generados. Si no se hace,
        se usará la fecha actual. El formato puede ser o bien un objeto
        'datetime', o bien una cadena en formato 'YYYY-MM-DD'.

        Antes de ejecutar la distribución, se comprobará que ésta es posible.
        Si no lo es, se lanzará un ValueError.

        """
        if not self.check():
            raise ValueError("La distribución no es posible.")

        date = date or datetime.now()
        if isinstance(date, str):
            date = datetime.strptime(date, "%Y-%m-%d")

        for sink in self._sinks:
            self._adapter.suite.events.new(
                id=-1,
                date=date,
                amount=sink.amount,
                category=sink.category,
                orig=self._source.target,
                dest=sink.target,
                concept=sink.concept,
                details=sink.details,
            )

    def __str__(self) -> str:
        return f"Distribution({self._source}, {len(self._sinks)} sumideros)"
