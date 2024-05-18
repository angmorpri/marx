# Python 3.10.11
# Creado: 31/01/2024
"""Gestión y seguimiento de préstamos.

Proporciona un mecanismo para gestionar préstamos en una contabilidad
gestionada por Marx.

Todos los eventos relacionados con un mismo préstamo deben presentar una
etiqueta, que tendrá forma "[...]" y se debe incluir en los detalles.

En líneas generales, un préstamo se compone de una serie de pagos y una serie
de devoluciones. Sin embargo, si un préstamo se conoce que no va a ser devuelto
en su totalidad, se puede generar un "impago" o "default". Esta situación se
representa en el balance mediante dos eventos: el primero, de impago, se
representa como un ingreso de valor equivalente a la cantidad restante por
recibir; el segundo, de ajuste, se representa como un gasto de igual valor; de
tal manera que, a efectos contables, el balance se mantiene equilibrado.

Para gestionar todo esto, se presenta una clase 'Loan', que representa un
préstamo en sí, y luego una interfaz 'LoansHandler', que permite encontrar
préstamos en un balance y generar eventos de impago cuando sean necesarios.

"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from marx.model import MarxDataStruct, Event


CLOSED = 1
OPEN = 0
DEFAULT = -1


@dataclass
class Loan:
    """Clase que representa un préstamo.

    Todos los eventos relacionados con un mismo préstamo son representados por
    una misma etiqueta ('tag').

    Un préstamo consiste en una serie de pagos ('paid') y una serie de
    devoluciones ('returned'). El saldo restante ('left') se calcula como la
    diferencia entre la cantidad total prestada ('total_paid') y la cantidad
    total devuelta ('total_returned').

    Por otro lado, si un préstamo se encuentra en situación de impago, existe
    un evento 'default' que representa el impago en sí, y que será equivalente
    a la cantidad restante por devolver. Además, existe también un evento
    'fix', equivalente a 'default', que sirve para ajustar el balance.

    Finalmente, 'status' indica el estado del préstamo, que puede ser abierto
    (0), cerrado (1) o en situación de impago (-1).

    """

    tag: str
    paid: list[Event] = field(default_factory=list)
    returned: list[Event] = field(default_factory=list)
    default: Event | None = None
    fix: Event | None = None

    @property
    def total_paid(self) -> float:
        """Cantidad total prestada."""
        return sum(event.amount for event in self.paid)

    @property
    def total_returned(self) -> float:
        """Cantidad total devuelta."""
        return sum(event.amount for event in self.returned)

    @property
    def left(self) -> float:
        """Cantidad restante por devolver."""
        return max(0.0, self.total_paid - self.total_returned)

    @property
    def status(self) -> int:
        """Estado del préstamo."""
        if self.left == 0:
            return CLOSED
        elif self.default is not None:
            return DEFAULT
        return OPEN


class LoansHandler:
    """Clase que gestiona los préstamos presentes en un balance.

    Permite encontrarlos mediante el método 'find' y generar eventos de impago
    mediante 'create_default'.

    El constructor sólo recibe una estructura de datos de Marx ya cargada.

    """

    def __init__(self, struct: MarxDataStruct) -> None:
        self.struct = struct
        self.loans = {}

    def find(
        self, from_date: datetime | None = None, to_date: datetime | None = None
    ) -> dict[str, Loan]:
        """Ubica todos los préstamos presentes en un balance, y los devuelve.

        Se puede especificar un rango de fechas para buscar los préstamos.
        Si no se especifica, se buscarán todos los préstamos en el balance.

        El diccionario devuelto tiene la forma {etiqueta: préstamo}.

        """
        # Fechas
        from_date = from_date or datetime(1970, 1, 1)
        to_date = to_date or datetime(2038, 1, 1)

        # Préstamos
        loans = {}
        loan_tag_pattern = r"\[([^\[\]]+)\]"
        for event in self.struct.events.search(
            lambda ev: from_date <= ev.date <= to_date,
            lambda ev: ev.category.code in ("B14", "A23", "B15", "A41"),
            status=CLOSED,
        ):
            if tags := re.findall(loan_tag_pattern, event.details):
                tag = tags[0]
                if tag not in loans:
                    loans[tag] = Loan(tag)
                if event.category.code == "B14":
                    loans[tag].paid.append(event)
                elif event.category.code == "A23":
                    loans[tag].returned.append(event)
                elif event.category.code == "B15":
                    loans[tag].default = event
                elif event.category.code == "A41":
                    loans[tag].fix = event
        return loans

    def create_default(
        self, loan: str | Loan, date: int | datetime | None = None, *, store: bool = False
    ) -> tuple[Event, Event]:
        """Genera eventos de impago para un préstamo.

        El préstamo puede ser proporcionado mediante su etiqueta o directamente
        como objeto Loan.

        Genera un evento de impago ('default') y otro de ajuste ('fix'). Si no
        se puede porque el préstamo ya está cerrado o en situación de impago,
        se lanzará una excepción.

        Se puede indicar una fecha que asignar a los eventos creados. Si no se
        proporciona, se tomará la fecha actual. Además, si se proporciona un
        entero, se asignarán tantos días después de la fecha del último pago
        recibido, o de la ejecución del préstamo si no se han registrado pagos.

        Si 'store' es True, los eventos se consolidan directamente en la base
        de datos. Por defecto, será False.

        Devuelve los eventos generados.

        """
        # Préstamo
        if isinstance(loan, str):
            loan = self.loans[loan]

        # Fecha
        date = date or datetime.now()
        if isinstance(date, int):
            if loan.returned:
                date = loan.returned[-1].date + timedelta(days=date)
            else:
                date = loan.paid[-1].date + timedelta(days=date)

        # Comprobaciones
        if loan.status != OPEN:
            raise ValueError("El préstamo está cerrado o ya está en situación de impago.")

        # Gasto por impago y ajuste
        default = Event(
            -1,
            date=date,
            amount=loan.left,
            category=self.struct.categories["B15"],
            orig=loan.paid[-1].orig,  # Cuenta origen del préstamo
            dest=loan.tag,  # Etiqueta del préstamo
            concept="Impago de préstamo",
            details=f"[{loan.tag}] {loan.paid[-1].dest}",
        )
        fix = Event(
            -1,
            date=date,
            amount=loan.left,
            category=self.struct.categories["A41"],
            orig="Impago de préstamo",
            dest=loan.paid[-1].orig,  # Cuenta origen del préstamo
            concept="Ajuste de balance por impago",
            details=f"[{loan.tag}]",
        )
        return default, fix
