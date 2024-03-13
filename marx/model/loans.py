# Python 3.10.11
# Creado: 31/01/2024
"""Gestión y seguimiento de préstamos.

Presenta la clase 'Loan', que representa un préstamo, y la función
'find_loans', que permite encontrar todos los préstamos, pagos e impagos
asociados a un mismo préstamo en una base de datos de Marx.

Un préstamo se compone de una serie de eventos, principalmente:
    - El préstamo en sí mismo (categoría B14).
    - Pagos recibidos (categoría A23).
    
Además, en caso de impago, se registran los siguientes eventos para dejar
constancia:
    - Impago de un préstamo (categoría B15).
    - Ajuste del balance por impago (categoría A41).
    
Un objeto Loan que represente un préstamo permite generar eventos de impago,
que luego pueden almacenarse en la base de datos.

"""

import re
from datetime import datetime, timedelta

from marx.model import MarxDataSuite, Event


CLOSED = "closed"
OPEN = "open"
DEFAULT = "default"


class Loan:
    """Representa un préstamo.

    Los cuatro tipo de eventos registrados se almacenan en:
        - 'loans': Préstamos. Pueden ser varios.
        - 'payments': Pagos. Pueden ser varios.
        - 'default': Impago.
        - 'fix': Ajuste por impagos.

    Además, se proporcionan las propiedades de seguimiento:
        - 'total': Cantidad total prestada.
        - 'left': Cantidad restante por devolver.
        - 'days_since': Días transcurridos desde el último pago hasta hoy.
        - 'status': Puede ser 'closed', si el préstamo está saldado; 'open', si
            el préstamo no está saldado pero hay expectativas de pago; o
            'default', si el préstamo no está saldado y no hay expectativas de
            pago, y se han registrado ya los eventos de impago.

    Finalmente, se proporciona el método 'generate_default', que genera dos
    eventos de impago, uno para el gasto por impago, y otro para el ajuste
    de balance.

    El constructor recibe la etiqueta de identificación del préstamo como
    único argumento. Opcionalmente puede recibir datos de la base de datos
    de contabilidad, aunque sólo se usarán para la generación de eventos de
    impago.

    """

    def __init__(self, tag: str, *, suite: MarxDataSuite | None) -> None:
        self.tag = tag
        self.suite = suite
        # Eventos
        self.loans = []
        self.payments = []
        self.default = None
        self.fix = None

    @property
    def total(self) -> float:
        """Cantidad total prestada."""
        return round(sum(event.amount for event in self.loans), 2)

    @property
    def left(self) -> float:
        """Cantidad restante por devolver."""
        return round(max(0.0, self.total - sum(event.amount for event in self.payments)), 2)

    @property
    def days_since(self) -> int:
        """Días transcurridos desde el último pago hasta hoy."""
        return (datetime.now() - self.payments[-1].date).days

    @property
    def status(self) -> str:
        """Estado del préstamo."""
        if self.left == 0:
            return CLOSED
        elif self.default is not None:
            return DEFAULT
        return OPEN

    def generate_default(
        self, date: int | datetime | None = None, *, suite: MarxDataSuite | None = None
    ) -> tuple[Event, Event]:
        """Genera los eventos de impago necesarios para el seguimiento.

        En concreto, genera un gasto por impago y, para compensar el balance,
        otro de ajuste por impago.

        Si no se proporciona una fecha que asignar a los eventos, se toma la
        fecha actual. Alternativamente, si se proporciona un entero como fecha,
        se asignarán tantos días después de la fecha del último pago, o de la
        ejecución del préstamo, si no se han registrado pagos.

        Si no se proporciona una suite de datos, se toma la suite de datos
        proporcionada al construir el objeto. Si no se proporcionó, se lanza
        una excepción.

        NOTA: Los eventos de impago generados NO se almacenan en la base de
        datos directamente, sino que se devuelven para que el usuario decida.

        """
        date = date or datetime.now()
        if isinstance(date, int):
            if self.payments:
                date = self.payments[-1].date + timedelta(days=date)
            else:
                date = self.loans[-1].date + timedelta(days=date)

        suite = suite or self.suite

        # Checks
        if suite is None:
            raise ValueError("No se proporcionó una suite de datos.")
        if self.status != OPEN:
            raise ValueError("El préstamo está cerrado o ya está en situación de impago.")

        # Gasto por impago
        self.default = Event(
            -1,
            date=date,
            amount=self.left,
            category=suite.categories["B15"],
            orig=self.loans[-1].orig,  # Cuenta origen del préstamo
            dest=self.tag,  # Etiqueta del préstamo
            concept="Impago de préstamo",
            details=f"[{self.tag}] {self.loans[-1].dest}",
        )
        # Ajuste por impago
        self.fix = Event(
            -1,
            date=date,
            amount=self.left,
            category=suite.categories["A41"],
            orig="Impago de préstamo",
            dest=self.loans[-1].orig,  # Cuenta origen del préstamo
            concept="Ajuste de balance por impago",
            details=f"[{self.tag}]",
        )
        return self.default, self.fix

    def __str__(self) -> str:
        return f"Préstamo {self.tag}: {self.total} ({self.left}) [{self.status.upper()}]"


def find_loans(
    suite: MarxDataSuite, *, from_date: datetime | None = None, to_date: datetime | None = None
) -> dict[str, Loan]:
    """Ubica todos los préstamos en la base de datos, y los devuelve.

    Se puede especificar un rango de fechas para buscar los préstamos. Si no se
    especifica, se buscarán todos los préstamos en la base de datos.

    Devuelve un diccionario con la forma {etiqueta: préstamo}.

    """
    # Fechas
    from_date = from_date or datetime(1970, 1, 1)
    to_date = to_date or datetime(2038, 1, 1)

    # Préstamos
    loans = {}
    loan_tag_pattern = r"\[([^\[\]]+)\]"
    for event in suite.events.search(
        lambda ev: from_date <= ev.date <= to_date,
        lambda ev: ev.category.code in ("B14", "A23", "B15", "A41"),
        status=CLOSED,
    ):
        if tags := re.findall(loan_tag_pattern, event.details):
            tag = tags[0]
            if tag not in loans:
                loans[tag] = Loan(tag, suite=suite)
            if event.category.code == "B14":
                loans[tag].loans.append(event)
            elif event.category.code == "A23":
                loans[tag].payments.append(event)
            elif event.category.code == "B15":
                loans[tag].default = event
            elif event.category.code == "A41":
                loans[tag].fix = event
    return loans
