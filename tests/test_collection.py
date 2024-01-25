# Python 3.10.11
# Creado: 24/01/2024
"""Test de la clase Collection."""
import os
import sys

MARX_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__) + "/marx"))
sys.path.append(os.path.dirname(MARX_DIR))


import random
from dataclasses import dataclass, field

from marx.model import Collection


@dataclass
class User:
    name: str
    age: int
    hobbies: list[str] = field(default_factory=list)


def test_manipulation():
    """Test de los métodos de manipulación de datos.

    También testea el comportamiento de los metadatos.

    """
    users = Collection(User, pkeys=["name", "age"])
    assert users.empty()
    print("Colección 'users' creada.\n")

    names = ["Juan", "María", "José", "Ana"]
    all_hobbies = ["leer", "escribir", "programar", "cocinar"]
    for _ in range(20):
        name = random.choice(names)
        age = random.randint(18, 65)
        n_hobbies = random.randint(0, 3)
        hobbies = random.sample(all_hobbies, n_hobbies)
        users.new(name, age, hobbies=hobbies)
    print("20 usuarios creados.")
    writers = users.search(lambda x: "escribir" in x.hobbies)
    print(f"Hay {len(writers)} escritores.")
    writers.show()
    print()
    print("Añadimos nuevos escritores")
    for _ in range(5):
        name = random.choice(names)
        age = random.randint(18, 65)
        writers.new(name, age, hobbies=["escribir"])
    print("Y creamos un nuevo usuario normal")
    users.new("Pedro", 25)
    print()
    for iid, user in users._active:
        print(iid, user)
    print()
    for iid, writer in writers._active:
        print(iid, writer)
    print()
    print("Eliminamos algunos escritores")
    writers.search(lambda x: x.name.startswith("M")).delete()
    print()
    for iid, user in users._active:
        print(iid, user)


if __name__ == "__main__":
    test_manipulation()
