# Python 3.10.11
# Creado: 01/08/2024
"""Herramienta para gestionar préstamos y deudas

Se considera "préstamo" cuando el usuario es el acreedor, esto es, es el que
presta dinero a otra persona. Se considera "deuda" en el caso contrario, cuando
es el usuario el deudor, el que ha sido prestado dinero. Para ambos casos,
existirán categorías duplicadas de "préstamo" y "deuda", cambiando el signo en
función de si el usuario es el acreedor o el deudor.

Todos los eventos que formen parte de un mismo préstamo o deuda serán
identificados por una etiqueta con formato "[<...>]", que debe aparecer en los
detalles del evento.

Se presenta la clase 'LoansHandler', a través de la cuál se pueden identificar
y listar todos los préstamos y deudas existentes y su estado hasta cierta
fecha, y también se puede generar un default en un préstamo, esto es, marcarlo
como que no se va a devolver o saldar (formalmente, lo único que hace es
añadir '!' delante de la etiqueta identificadora del préstamo).

Se apoya en el modelo 'Loan', que representa un préstamo o deuda.

"""

from __future__ import annotations

import re
from datetime import datetime

from marx.models import Event, MarxDataStruct
from marx.util.factory import Factory


LOAN_TAG_PATTERN = r"\[.*?\]"

DEBTOR_IN = "A31"  # Préstamos recibidos
DEBTOR_OUT = "B61"  # Deudas a pagar
CREDITOR_IN = "A32"  # Deudas a cobrar
CREDITOR_OUT = "B62"  # Préstamos concedidos

DEFAULT_MARK = "!"


class Loan:
    """Préstamo o deuda

    El constructor recibe la etiqueta identificativa a la que pertenece, y, a
    modo informativo, la fecha hasta la que extraen eventos relacionados con
    ésta.

    """

    DEBTOR = -1  # yo DEBO dinero
    CREDITOR = 1  # yo PRESTO dinero

    ONGOING = 0
    CLOSED = 1
    DEFAULT = -1

    def __init__(self, tag: str, stop_date: datetime):
        self.tag = tag.strip("[]")
        self.default = False
        if self.tag.startswith(DEFAULT_MARK):
            self.tag = self.tag[1:]
            self.default = True
        self.stop_date = stop_date
        self.events = []

    def add(self, event: Event) -> None:
        """Añade un evento al préstamo o deuda"""
        self.events.append(event)

    @property
    def position(self) -> int:
        """Posición del usuario en el préstamo o deuda"""
        catcode = self.events[-1].category.code
        if catcode in (DEBTOR_IN, DEBTOR_OUT):
            return Loan.DEBTOR
        if catcode in (CREDITOR_IN, CREDITOR_OUT):
            return Loan.CREDITOR

    @property
    def status(self) -> int:
        """Estado del préstamo o deuda"""
        if self.default:
            return Loan.DEFAULT
        elif self.remaining != 0:
            return Loan.ONGOING
        return Loan.CLOSED

    @property
    def start_date(self) -> datetime:
        """Fecha de inicio del préstamo o deuda"""
        return list(sorted(self.events, key=lambda x: x.date))[0].date

    @property
    def end_date(self) -> datetime | None:
        """Fecha de fin del préstamo o deuda"""
        if self.status in (Loan.CLOSED, Loan.DEFAULT):
            return list(sorted(self.events, key=lambda x: x.date))[-1].date
        return None

    @property
    def amount(self) -> float:
        """Cantidad prestada o adeudada"""
        return sum(e.amount for e in self.events if e.category.code in (DEBTOR_IN, CREDITOR_OUT))

    @property
    def paid(self) -> float:
        """Cantidad devuelta o saldada"""
        return sum(e.amount for e in self.events if e.category.code in (DEBTOR_OUT, CREDITOR_IN))

    @property
    def remaining(self) -> float:
        """Cantidad restante por devolver o saldar"""
        return max(0.0, self.amount - self.paid)

    @property
    def surplus(self) -> float:
        """Cantidad devuelta o saldada de más"""
        return max(0.0, self.paid - self.amount)

    @property
    def counterparts(self) -> str:
        """Prestamista o deudor"""
        cps = set()
        for event in self.events:
            cps.add(event.counterpart.name)
        return "; ".join(cps)

    def __eq__(self, other: Loan) -> bool:
        return self.tag == other.tag

    def __lt__(self, other: Loan) -> bool:
        return (self.start_date, self.tag) < (other.start_date, other.tag)

    def __str__(self) -> str:
        default = "!" if self.default else ""
        pos = "DEBTOR" if self.position == Loan.DEBTOR else "CREDITOR"
        return f"Loan([{default}{self.tag}] {pos}, {self.amount:.2f} / {self.paid:.2f} / {self.remaining:.2f} €)"

    def show(self) -> None:
        tag = f"[{self.tag}]"
        pos = "DEBTOR" if self.position == Loan.DEBTOR else "CREDITOR"
        status = (
            "OPEN"
            if self.status == Loan.ONGOING
            else "CLOSED" if self.status == Loan.CLOSED else "DEFAULT"
        )
        span = (
            f"{self.start_date:%Y/%m/%d} - {self.end_date:%Y/%m/%d}"
            if self.end_date
            else f"{self.start_date:%Y/%m/%d} - "
        )
        print(f"{tag} {pos} / {status} ({span})")
        print(f"| T: {self.amount:.2f} € / P: {self.paid:.2f} € / R: {self.remaining:.2f} €")
        print(f"| {self.counterparts}")
        print(f"| {len(self.events)} events")
        print()


class LoansHandler:
    """Gestor de préstamos y deudas

    Permite identificar préstamos y deudas y sus estados hasta cierta fecha, y,
    también, generar defaults en préstamos y deudas.

    El constructor recibe la estructura de datos Marx que se esté usando. Para
    identificar préstamos, se debe llamar al método 'find' con la fecha hasta
    la que se desea buscar. Para generar defaults, se debe llamar al método
    'default' junto con la etiqueta del préstamo o deuda a aplicar.

    """

    def __init__(self, data: MarxDataStruct):
        self.data = data

    def find(self, stop_date: datetime) -> list[Loan]:
        """Encuentra los préstamos y deudas abiertos a cierta fecha

        Devuelve una lista de objetos 'Loan', representando todos los préstamos
        y deudas encontrados y sus estados hasta la fecha especificada.

        """
        loans = {}
        for event in self.data.events.subset(
            lambda x: x.date <= stop_date,
            lambda x: re.search(LOAN_TAG_PATTERN, x.details),
        ):
            tags = re.findall(LOAN_TAG_PATTERN, event.details)
            if tags:
                tag = tags[0]
                if tag not in loans:
                    loans[tag] = Loan(tag, stop_date)
                loans[tag].add(event)
        return list(sorted(loans.values()))

    def default(self, tag: str) -> Factory[Event]:
        """Genera un default en un préstamo o deuda"""
        loans = self.find(datetime.now())
        target = next((l for l in loans if l.tag == tag), None)
        if target is None:
            raise ValueError(f"[Loan] Préstamo o deuda con etiqueta {tag!r} no encontrado")
        if target.status == Loan.CLOSED:
            raise ValueError(f"[Loan] Préstamo o deuda con etiqueta {tag!r} ya cerrado")
        if target.status == Loan.DEFAULT:
            return
        events = self.data.events.subset()
        for event in target.events:
            event.details = event.details.replace(f"[{tag}]", f"[!{tag}]")
            events.join(event)
        return events
