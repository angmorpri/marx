# Python 3.10.11
# Creado: 24/01/2024
"""Para hacer pequeñas pruebas de código."""
import weakref
from copy import deepcopy
from dataclasses import dataclass


@dataclass
class User:
    name: str
    age: int


class RanUser:
    def __init__(self, name: str, age: int):
        self.name = name
        self.age = age


if __name__ == "__main__":
    print(RanUser.__dict__)
