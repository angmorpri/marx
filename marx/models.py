# Python 3.10.11
# Creado: 08/07/2024
"""Modelos de datos"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar


@dataclass
class Account:
    """Cuenta contable"""

    id: int
    name: str
    order: int = 100
    color: str = "#FFFFFF"
    disabled: bool = False

    @property
    def rid(self) -> int:
        """ID real de la cuenta"""
        return self.id

    @property
    def repr_name(self) -> str:
        return "@" + self.name

    def serialize(self) -> dict[str, Any]:
        """Serializa la cuenta"""
        return {
            "id": self.id,
            "name": self.name,
            "order": self.order,
            "color": self.color,
            "disabled": self.disabled,
        }

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Account):
            return self.id == other.id
        return False

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, Account):
            return (self.order, self.name) < (other.order, other.name)
        return False

    def __format__(self, format_spec: str) -> str:
        return self.name.__format__(format_spec)

    def __str__(self) -> str:
        return f"Account({self.id}, {self.name!r})"


@dataclass
class Counterpart:
    """Contraparte"""

    name: str

    @property
    def repr_name(self) -> str:
        return self.name

    def serialize(self) -> dict[str, Any]:
        """Serializa la contraparte"""
        return {"name": self.name}

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Counterpart):
            return self.name == other.name
        return False

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, Counterpart):
            return self.name < other.name
        elif isinstance(other, Account):
            return True
        return False

    def __format__(self, format_spec: str) -> str:
        return self.name.__format__(format_spec)

    def __str__(self) -> str:
        return self.name


@dataclass
class Category:
    """Categoría de un traslado o transacción"""

    id: int  # +: transacción, -: traslado
    name: str
    icon: int = 0
    color: str = "#FFFFFF"
    disabled: bool = False

    # Tipos
    TRANSFER: ClassVar[int] = 0
    TRANSACTION: ClassVar[int] = 1

    @property
    def rid(self) -> int:
        """ID real de la categoría"""
        return abs(self.id)

    @property
    def type(self) -> int:
        """Tipo de la categoría"""
        return self.TRANSFER if self.code.startswith("T") else self.TRANSACTION

    @property
    def code(self) -> str:
        """Código de la categoría"""
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

    def is_income(self) -> bool:
        """Comprueba si la categoría es de ingreso."""
        return self.code.startswith("A")

    def serialize(self) -> dict[str, Any]:
        """Serializa la categoría"""
        return {
            "id": self.id,
            "name": self.name,
            "icon": self.icon,
            "color": self.color,
            "disabled": self.disabled,
        }

    def __eq__(self, other: Category) -> bool:
        """Compara dos categorías."""
        return self.code == other.code

    def __lt__(self, other: Category) -> bool:
        """Compara dos categorías."""
        return self.code < other.code

    def __str__(self) -> str:
        return f"Category({self.id}, {self.code!r}, {self.title!r})"


@dataclass
class Event:
    """Evento contable, que puede ser una transacción o un traslado"""

    id: int | complex  # +: transacción, -: traslado, i: evento recurrente
    date: datetime
    amount: float
    category: Category
    orig: Account | Counterpart
    dest: Account | Counterpart
    concept: str = ""
    details: str = ""
    status: int = 1  # 0: abierto, 1: cerrado
    rsource: complex = -1  # ID del evento recurrente, si no procede, -1

    # Tipos
    TRANSFER: ClassVar[int] = 0
    TRANSACTION: ClassVar[int] = 1
    RECURRING: ClassVar[int] = 2

    # Flujos
    INCOME: ClassVar[int] = 1
    EXPENSE: ClassVar[int] = -1
    # TRANSFER: ClassVar[int] = 0   # Ya definido como "tipo"

    # Estado
    OPEN: ClassVar[int] = 0
    CLOSED: ClassVar[int] = 1

    def __post_init__(self):
        if isinstance(self.orig, str):
            self.orig = Counterpart(self.orig)
        if isinstance(self.dest, str):
            self.dest = Counterpart(self.dest)

    @property
    def rid(self) -> int:
        """ID real del evento"""
        return int(abs(self.id))

    @property
    def type(self) -> int:
        """Tipo del evento"""
        if self.category.type == self.category.TRANSFER:
            return self.TRANSFER
        elif isinstance(self.id, complex):
            return self.RECURRING
        return self.TRANSACTION

    @property
    def flow(self) -> int:
        """Flujo del evento"""
        if isinstance(self.orig, Account) and isinstance(self.dest, Account):
            return self.TRANSFER
        elif isinstance(self.orig, Account):
            return self.EXPENSE
        elif isinstance(self.dest, Account):
            return self.INCOME

    @property
    def account(self) -> Account:
        """Cuenta del evento"""
        return self.dest if self.flow == self.INCOME else self.orig

    @property
    def counterpart(self) -> Counterpart:
        """Contraparte del evento"""
        return self.orig if self.flow == self.INCOME else self.dest

    def is_from_recurring(self) -> bool:
        """Comprueba si el evento procede de un evento recurrente."""
        return self.rsource != -1

    def serialize(self) -> dict[str, Any]:
        """Serializa el evento"""
        return {
            "id": self.id,
            "date": self.date,
            "amount": self.amount,
            "category": self.category.serialize(),
            "orig": self.orig.serialize(),
            "dest": self.dest.serialize(),
            "concept": self.concept,
            "details": self.details,
            "status": self.status,
            "rsource": self.rsource,
            "flow": self.flow,
        }

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
        return (self.date, self.amount, self.category, self.orig, self.dest) < (
            other.date,
            other.amount,
            other.category,
            other.orig,
            other.dest,
        )

    def __str__(self) -> str:
        id = f"R{self.rid}" if self.type == self.RECURRING else self.id
        sign = ["=", "+", "-"][self.flow]
        amount = f"{sign}{self.amount:8.2f}"
        category = self.category.code
        orig = self.orig.repr_name
        dest = self.dest.repr_name
        return f"Event({id}, {self.date:%Y-%m-%d}, {amount}, {orig!r} -> {dest!r}, {category!r}, {self.concept!r})"
