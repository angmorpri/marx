# Python 3.10.11
# Creado: 02/08/2024
"""Test de la clase Factory."""
import os
from random import choice, randint
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

    # new(), register()
    new = factory.new("Juan", 1)
    new.dbg_show("NEW")
    myobj = MyClass("Ana", 2)
    reg = factory.register(myobj)
    reg.dbg_show("REG")
    factory.dbg_show("FACTORY AFTER NEW AND REGISTER")
    factory.new("Pedro", 3)
    factory.new("María", 4)
    factory.new("José", 5)
    factory.new("Carla", 6)

    # __getitem__(), delete(), all, any, active
    subset = factory[3:]
    subset.dbg_show("SUBSET")
    subset.delete()
    subset.dbg_show("SUBSET AFTER DELETE")
    subset.any.dbg_show("SUBSET AFTER DELETE WITH ANY")
    factory.dbg_show("FACTORY AFTER DELETE")
    factory.any.dbg_show("FACTORY AFTER DELETE WITH ANY")
    factory.any.active.dbg_show("FACTORY ACTIVE AFTER DELETE WITH ANY AND THEN ACTIVE")

    # select() y __getitem__()
    print(factory.select("name", "value"))
    print(factory.any.value)
    print()

    # update() y __setattr__()
    factory.update(value=10)
    factory.dbg_show("FACTORY AFTER UPDATE")
    factory.any.dbg_show("FACTORY AFTER UPDATE WITH ANY")
    subset.all.value = 20
    factory.dbg_show("FACTORY AFTER SUBSET.ALL IS UPDATED")

    # pull() y pullone()
    print(factory.pull())
    print(factory.pullone())
    print()

    # sort()
    x = factory.all.sort("name")
    x.dbg_show("SORTED")
    x.all.dbg_show("SORTED ALL")
    x = subset.sort("name")
    x.dbg_show("SORTED SUBSET")

    # subset()
    for item in factory:
        item.value = randint(1, 10)
    x = factory.subset(lambda x: x.value >= 5)
    x.dbg_show("SUBSET WITH LAMBDA FILTER")
    for item in factory:
        item.name = choice(["Bob", "Alice"])
    x = factory.subset(lambda x: x.value >= 5, name="Bob")
    x.dbg_show("SUBSET WITH LAMBDA FILTER AND KEY FILTER")
    x.all.dbg_show("SUBSET WITH LAMBDA FILTER AND KEY FILTER (ALL)")

    # fallback()
    fb = factory.subset(name="John").fallback(name="John", value=100)
    fb.dbg_show("FALLBACK ITEM")
    factory.dbg_show("FACTORY AFTER FALLBACK")

    # subset() meta
    factory.any.dbg_show("CURRENT STATUS")
    print("META DELETED:")
    for item in factory.meta_deleted:
        print(item)
    print()
    print("META CHANGED:")
    for item, changes in factory.meta_changed:
        print(item, changes)

    # representación
    print(factory)
    factory.show()


if __name__ == "__main__":
    test_creation()
