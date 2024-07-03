# Python 3.10.11
# Creado: 02/08/2024
"""Test de la clase Factory."""
import os
import sys

MARX_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__) + "/marx"))
sys.path.append(os.path.dirname(MARX_DIR))


from marx.factory import Factory


class MyClass:
    def __init__(self, name: str, value: int) -> None:
        self.name = name
        self.value = value

    def __repr__(self) -> str:
        return f"{self.name} ({self.value})"


def test_creation():
    factory = Factory(MyClass)

    # new(), register(), __iter__(), pull(), pullone()
    new = factory.new("First", 1)
    print(factory)
    myobj = MyClass("Second", 2)
    reg = factory.register(myobj)
    print(factory)
    for item in factory:
        print(" - ", item.pull(), item.pullone(), item, type(item), sep="; ")
    print()
    for item in factory:
        print(" - ", item.pull(), item.pullone(), item, type(item), sep="; ")

    print()

    # update(), __setattr__()
    factory.update(value=10)
    for item in factory:
        print(item.pull(), item.pullone(), item, type(item), sep="; ")
    factory.value = 20
    for item in factory:
        print(item.pull(), item.pullone(), item, type(item), sep="; ")


if __name__ == "__main__":
    test_creation()
