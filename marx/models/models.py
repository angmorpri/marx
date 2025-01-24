# Python 3.10.11
# Creado: 08/07/2024
"""Modelos de datos"""

from __future__ import annotations

import re
from collections import namedtuple
from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar

MarxDataStruct = namedtuple("MarxDataStruct", ["accounts", "categories", "events"])


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
            "repr_name": self.repr_name,
            "order": self.order,
            "color": self.color,
            "disabled": self.disabled,
        }

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Account):
            return self.id == other.id
        elif isinstance(other, (Counterpart, str)):
            return False
        raise TypeError(
            f"Unsupported comparison between 'Account' and {type(other).__name__!r}"
        )

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, Account):
            return (self.order, self.name) < (other.order, other.name)
        elif isinstance(other, (Counterpart, str)):
            return False
        raise TypeError(
            f"Unsupported comparison between 'Account' and {type(other).__name__!r}"
        )

    def __contains__(self, other: Any) -> bool:
        if isinstance(other, str):
            return other in self.name
        raise TypeError(
            f"Unsupported operation between 'Account' and {type(other).__name__!r}"
        )

    def __str__(self) -> str:
        id = "----" if self.id == -1 else f"{self.rid:04d}"
        return f"Account(#{id}, {self.repr_name}, {self.order}, {self.color})"


@dataclass
class Counterpart:
    """Contraparte"""

    name: str

    @property
    def repr_name(self) -> str:
        return self.name

    def serialize(self) -> dict[str, Any]:
        """Serializa la contraparte"""
        return {"name": self.name, "repr_name": self.repr_name}

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Counterpart):
            return self.name == other.name
        elif isinstance(other, str):
            return self.name == other
        elif isinstance(other, Account):
            return False
        raise TypeError(
            f"Unsupported comparison between 'Counterpart' and {type(other).__name__!r}"
        )

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, Counterpart):
            return self.name < other.name
        elif isinstance(other, str):
            return self.name < other
        elif isinstance(other, Account):
            return True
        raise TypeError(
            f"Unsupported comparison between 'Counterpart' and {type(other).__name__!r}"
        )

    def __contains__(self, other: Any) -> bool:
        if isinstance(other, str):
            return other in self.name
        raise TypeError(
            f"Unsupported operation between 'Counterpart' and {type(other).__name__!r}"
        )

    def __format__(self, format_spec: str) -> str:
        return self.name.__format__(format_spec)

    def __str__(self) -> str:
        return f"Counterpart(#9999, {self.repr_name})"


@dataclass
class Category:
    """Categoría de un traslado o transacción"""

    id: int  # +: transacción, -: traslado
    name: str
    type: int
    icon: int = 0
    color: str = "#FFFFFF"
    disabled: bool = False

    # Tipos
    EXPENSE: ClassVar[int] = -1
    TRANSFER: ClassVar[int] = 0
    INCOME: ClassVar[int] = 1

    @property
    def rid(self) -> int:
        """ID real de la categoría"""
        return abs(self.id)

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
        return self.type == self.INCOME

    def serialize(self) -> dict[str, Any]:
        """Serializa la categoría"""
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "title": self.title,
            "icon": self.icon,
            "color": self.color,
            "type": self.type,
            "disabled": self.disabled,
        }

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Category):
            return self.id == other.id
        elif isinstance(other, str):
            return False
        raise TypeError(
            f"Unsupported comparison between 'Category' and {type(other).__name__!r}"
        )

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, Category):
            if self.code == other.code:
                raise ValueError("Categories with the same code")
            return self.code < other.code
        elif isinstance(other, str):
            return False
        raise TypeError(
            f"Unsupported comparison between 'Category' and {type(other).__name__!r}"
        )

    def __contains__(self, other: Any) -> bool:
        """Comprueba códigos de categoría.

        Admite '*' como comodín.

        """
        if isinstance(other, str):
            if len(other) > 3:
                return False
            matching_code = other + "\d" * (len(self.code) - len(other))
            if matching_code[0] == "*":
                matching_code = "[A-Z]" + matching_code[1:]
            matching_code = matching_code.replace("*", "\d")
            return bool(re.match(matching_code, self.code))
        raise TypeError(
            f"Unsupported operation between 'Category' and {type(other).__name__!r}"
        )

    def __str__(self) -> str:
        id = "----" if self.id == -1 else f"{self.rid:04d}"
        symbol = (
            "+"
            if self.type == self.INCOME
            else "-" if self.type == self.EXPENSE else "="
        )
        return f"Category(#{id}, {symbol} [{self.code}] {self.title}, {self.icon}, {self.color})"


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
            "date": self.date.strftime("%Y-%m-%d"),
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

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Event):
            return self.id == other.id
        raise TypeError(
            f"Unsupported comparison between 'Event' and {type(other).__name__!r}"
        )

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, Event):
            return (self.date, self.type, self.flow, self.amount, self.concept) < (
                other.date,
                other.type,
                other.flow,
                other.amount,
                other.concept,
            )
        raise TypeError(
            f"Unsupported comparison between 'Event' and {type(other).__name__!r}"
        )

    def __contains__(self, other: Any) -> bool:
        if isinstance(other, (Account, Counterpart)):
            return other in (self.orig, self.dest)
        elif isinstance(other, Category):
            return other == self.category
        elif isinstance(other, Event):
            if other.type == self.RECURRING:
                return other.id == self.rsource
            return False
        elif isinstance(other, str):
            return other in self.concept
        raise TypeError(
            f"Unsupported operation between 'Event' and {type(other).__name__!r}"
        )

    def __str__(self) -> str:
        id = "----" if self.id == -1 else f"{self.rid:04d}"
        sign = (
            "+"
            if self.flow == self.INCOME
            else "-" if self.flow == self.EXPENSE else "="
        )
        amount = f"{sign} {self.amount:8.2f} €"
        shconcept = self.concept
        if len(self.concept) > 20:
            shconcept = self.concept[:17] + "..."
        status = "OPEN" if self.status == self.OPEN else "CLOSED"
        if self.rsource == -1:
            return f"Event(#{id}, {amount}, {self.date:%Y-%m-%d}, {shconcept!r}, [{self.category.code}] {self.orig.repr_name} -> {self.dest.repr_name}, {status})"
        else:
            return f"Event(#{id}, {amount}, {self.date:%Y-%m-%d}, {shconcept!r}, [{self.category.code}] {self.orig.repr_name} -> {self.dest.repr_name}, {status}, RSOURCE {self.rsource})"
