# Python 3.10.11
# Creado: 31/01/2024
"""Clase para representar los modelos de datos usados por Marx.

Presenta las siguientes clases para mapear todos los datos usados por el
programa:

    - Account: Identifica una cuenta bancaria.
    - Category: Identifica una categoría de ingreso, gasto o traslado.
    - Note: Identifica una nota, entendida en los mismos términos que la app.
    - Event: Identifica un evento. Este puede ser o bien una transacción
        (ingreso o gasto), un traslado, o una operación recurrente.

Todas las clases tienen un atributo común 'id' para identificarlas. Debido a
que algunas de ellas agrupan datos que originalmente podían tener el mismo id,
se usan mecanismos para diferenciarlos; pero si se quiere acceder al id real,
se puede usar el atributo 'rid'.

Cuando se crea un objeto nuevo de una de estas clases, por defecto se le asigna
id -1 (NEW), para señalar que el objeto no está almacenado en la base de datos
todavía. Al guardar, se le asigna un id válido.

Cada una de estas clases pueden usarse individualmente, pero lo más común es
usarlas a través de una colección.

"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


NEW = -1

INCOME = 1
EXPENSE = -1
TRANSFER = 0

NT_NOTE = "note"
NT_PAYEE = "payee"
NT_PAYER = "payer"


@dataclass
class Account:
    """Representa una cuenta bancaria.

    Junto con el ID, se almacena el nombre ('name'), el orden ('order') en el
    que debe aparecer representada respecto a otras, y el color ('color')
    asignado en la app.

    """

    id: int
    name: str
    order: int = 100
    color: str = "#FFFFFF"

    @property
    def rid(self):
        """Devuelve el id real de la cuenta."""
        return self.id

    def __eq__(self, other: Account) -> bool:
        """Compara dos cuentas."""
        return self.name == other.name

    def __lt__(self, other: Account) -> bool:
        """Compara dos cuentas."""
        return (self.order, self.name) < (other.order, other.name)

    def __str__(self) -> str:
        return f"[{self.rid:04}] {self.name:20} ({self.order:3}, {self.color})"

    def __format__(self, spec: str) -> str:
        return self.name.__format__(spec)


@dataclass
class Category:
    """Representa una categoría asociada a un evento.

    Las categorías pueden ser de tres tipos: ingreso, gasto o traslado. El
    tipo se almacena en el atributo 'type', que puede ser 1 (ingreso), 0
    (traslado) o -1 (gasto).

    Además, todas las categorías tienen un nombre ('name') (compuesto a su vez
    por un código ('code') y un título ('title')), un color ('color'), y un
    icono ('icon') para la app identificado por su ID.

    """

    id: int
    name: str
    icon: int = 0
    color: str = "#FFFFFF"

    @property
    def rid(self):
        """Devuelve el id real de la categoría."""
        return abs(self.id)

    @property
    def type(self):
        """Devuelve el tipo de la categoría."""
        if self.id < 0:
            return 0
        elif self.code.startswith("A"):
            return 1
        return -1

    @property
    def code(self):
        """Devuelve el código de la categoría."""
        return self.name.split(". ")[0]

    @code.setter
    def code(self, value):
        """Cambia el código de la categoría."""
        self.name = f"{value}. {self.title}"

    @property
    def title(self):
        """Devuelve el título de la categoría."""
        return self.name.split(". ")[1]

    @title.setter
    def title(self, value):
        """Cambia el título de la categoría."""
        self.name = f"{self.code}. {value}"

    def __eq__(self, other: Category) -> bool:
        """Compara dos categorías."""
        return self.code == other.code

    def __lt__(self, other: Category) -> bool:
        """Compara dos categorías."""
        return self.code < other.code

    def __str__(self) -> str:
        return f"[{self.rid:04}] {self.name:30} ({self.icon:3}, {self.color})"


@dataclass
class Note:
    """Representa una nota.

    Las notas son textos que usa la app para facilitar la repetición de nombres
    de contrapartes en transacciones, o de descripciones en eventos en general.

    El texto es accesible mediante 'text'. Para identificar a qué concepto
    aplica la nota, se presenta el atributo 'target', que puede valer 'note',
    'payee' o 'payer'.

    """

    id: int
    text: str = ""
    target: str = "note"

    @property
    def rid(self):
        """Devuelve el id real de la nota."""
        return self.id

    def __eq__(self, other: Note) -> bool:
        """Compara dos notas."""
        return self.text == other.text

    def __lt__(self, other: Note) -> bool:
        """Compara dos notas."""
        return self.text < other.text

    def __str__(self) -> str:
        return f"[{self.rid:04}] {self.text:20} ({self.target})"


@dataclass
class Event:
    """Representa un evento contable.

    Se define como evento contable a cualquier transacción o traslado de
    capital, actual, futuro o programado, entre una cuenta bancaria y una
    contraparte, o entre dos cuentas bancarias.

    Todo evento contable tiene una fecha ('date') en la que sucede o sucederá,
    una cantidad asociada ('amount'), una categoría ('category'), un origen
    ('orig') y un destino ('dest'), que pueden ser o bien cuentas bancarias, o
    bien contrapartes (representadas mediante cadenas de texto). También
    disponen de un concepto ('concept') y unos detalles ('details'); de un
    tipo identificador ('type'), que puede ser 1 (ingreso), 0 (traslado) o -1
    (gasto); un estatus ('status'), que puede ser pendiente (0), realizado (1)
    o recurrente (2). Finalmente, aquellos eventos consolidados a partir de un
    evento recurrente, tendrán el atributo 'rsource' señalando al ID del evento
    del que provienen.

    Los eventos de ID positivo serán transacciones, los de ID negativo,
    traslados, y los de ID complejo, eventos recurrentes.

    """

    id: int | complex
    date: datetime
    amount: float
    category: Category
    orig: Account | str
    dest: Account | str
    concept: str = ""
    details: str = ""
    status: str = "closed"  # "open", "closed", "recurring"
    rsource: int | None = None

    @property
    def rid(self):
        """Devuelve el id real del evento."""
        return int(abs(self.id))

    @property
    def type(self):
        """Devuelve el tipo del evento."""
        if isinstance(self.orig, Account) and isinstance(self.dest, Account):
            return 0
        elif isinstance(self.orig, Account):
            return -1
        return 1

    @property
    def account(self) -> Account:
        if self.type == INCOME:
            return self.dest
        elif self.type == EXPENSE:
            return self.orig
        elif self.type == TRANSFER:
            return self.orig

    @property
    def counterpart(self) -> str | Account:
        """En el caso de traslados, devuelve la cuenta destino."""
        if self.type == INCOME:
            return self.orig
        elif self.type == EXPENSE:
            return self.dest
        elif self.type == TRANSFER:
            return self.dest

    @property
    def isbill(self) -> bool:
        """Devuelve True si el evento es una operación recurrente."""
        return self.rsource is not None

    def __eq__(self, other: Event) -> bool:
        """Compara dos eventos."""
        return (self.date, self.amount, self.category, self.orig, self.dest) == (
            other.date,
            other.amount,
            other.category,
            other.orig,
            other.dest,
        )

    def __lt__(self, other: Event) -> bool:
        """Compara dos eventos."""
        return (self.status, self.date, self.amount, self.category, self.orig, self.dest) < (
            other.status,
            other.date,
            other.amount,
            other.category,
            other.orig,
            other.dest,
        )

    def __str__(self) -> str:
        head = f"[{self.rid:04}] {self.date:%d-%m-%Y}"
        sign = ["≷", "+", "-"][self.type]
        amount = f"{sign}{self.amount:10.2f}"
        category = f"{self.category.name:30}"
        flow = f"{self.orig:20} → {self.dest:20}"
        if self.status == "recurring":
            flow = f"{flow} [R]"
        elif self.status == "open":
            flow = f"{flow} [0]"
        if self.rsource and self.rsource != -1:
            flow = f"{flow} [P={self.rsource}]"
        return f"{head} {amount} {category} {flow} {self.concept}"


if __name__ == "__main__":
    cat = Category(1, "A21. Alquiler")
    print(cat.code, cat.title)
    cat.code = "X99"
    print(cat)
