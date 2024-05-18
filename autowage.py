# Python 3.10.11
# Creado: 26/02/2024
"""Genera automáticamente los eventos derivados de la nómina."""
from datetime import datetime
from tkinter.filedialog import askopenfilename

from marx.automation import WageParser
from marx.model import MarxMapper
from marx.util import get_most_recent_db


WAGES_DIR = r"C:\Users\angel\OneDrive - Telefonica\Documentos\Nóminas"


if __name__ == "__main__":
    print("[AUTO WAGE]")
    path = get_most_recent_db("G:/Mi unidad/MiBilletera Backups")
    print("Usando: ", path)
    adapter = MarxMapper(path)
    adapter.load()

    # Fecha
    date = None
    while not date:
        date = input("Fecha de los eventos (formato dd/mm/yyyy): ")
        if not date:
            date = datetime.now()
        else:
            try:
                date = datetime.strptime(date, "%d/%m/%Y")
            except ValueError:
                print("Fecha inválida")

    # WageParser
    wp = WageParser(adapter.struct)
    wage = askopenfilename(initialdir=WAGES_DIR)
    wp.parse(wage, date=date, verbose=True)

    path = adapter.save(prefix="AUTOWAGE")
    print("Resultado almacenado en", path)
