# Python 3.10.11
# Creado: 24/01/2024
"""Para hacer pequeñas pruebas de código."""
import re

from marx.model import RawAdapter


PATH = "G:/Mi unidad/MiBilletera Backups/Ene_26_2024_ExpensoDB"


if __name__ == "__main__":
    adapter = RawAdapter(PATH)
    suite = adapter.load()
    tcats = suite.notes.search(lambda x: re.match(r"^T\d{2}\. .+", x.text))
    tcats.update(text=lambda x: "[" + x + "]")
    suite.notes.show()
    adapter.save()
    print("OK")
