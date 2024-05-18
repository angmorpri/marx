# Python 3.10.11
# Creado: 31/01/2024
"""Corrige las categorías de traslados para que se muestren entre corchetes.

También garantiza que todo traslado tenga una categoría asociada.

"""
import os
import sys

MARX_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__) + "/marx"))
sys.path.append(os.path.dirname(MARX_DIR))


import re

from marx.model import BaseMapper
from marx.util import get_most_recent_db


CATEGORY_PATTERN = "^[A-Z][A-Z0-9][A-Z0-9]\.\s.*"


def fix_transfers(adapter: BaseMapper) -> None:
    """Corrige la forma en la que las categorías de traslados se muestran.

    Como la aplicación no tiene categorías integradas para los traslados, la
    idea es usar la primera línea de las notas para indicarlas. Actualmente,
    sin embargo, no hay garantía de ello y, además, cuando se representa, lo
    hace directamente. La idea es que se muestre entre corchetes.

    Allí donde no hubiere categoría, se creará una por defecto "T99. Default".

    """
    suite = adapter.load()
    for trans in suite.transfers:
        maybe_cat, *rest = trans.note.strip().split("\n")
        if not re.match(CATEGORY_PATTERN, maybe_cat):
            print(f">>> No cumple: {maybe_cat}. Se autoasigna por defecto.")
            trans.note = "[T99. Default]\n" + trans.note
        elif maybe_cat.startswith("[") and maybe_cat.endswith("]"):
            print(f">>> Ya está bien: {maybe_cat}")
        else:
            trans.note = "[" + maybe_cat + "]\n" + "\n".join(rest)
        trans.note = trans.note.strip()
        print(">>> Hecho")


def fix_notes(adapter: BaseMapper) -> None:
    """Corrige las notas que se usan para representar las categorías."""
    suite = adapter.load()
    for note in suite.notes:
        if note.text.startswith("[") and note.text.endswith("]"):
            cat = note.text[1:-1]
            if re.match(CATEGORY_PATTERN, cat):
                print(f">>> Ya está bien: {note.text}")
            else:
                print(f">>> Marcado como categoría, pero no cumple: {note.text}")
        elif re.match(CATEGORY_PATTERN, note.text):
            note.text = "[" + note.text + "]"
            print(f">>> Corregido: {note.text}")
    print(">>> Hecho")


if __name__ == "__main__":
    most_recent = get_most_recent_db("G:/Mi unidad/MiBilletera Backups")
    input(f"Usando: {most_recent}")
    adapter = BaseMapper(most_recent)
    adapter.load()

    fix_transfers(adapter)
    for trans in adapter.suite.transfers:
        print(trans.note)
        print("-----------------------------")
    print("\n\n")

    fix_notes(adapter)
    for note in adapter.suite.notes:
        print(note.text)

    adapter.save()
