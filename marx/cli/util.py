# Python 3.10.11
# Creado: 09/08/2024
"""Utilidades exclusivas para el cliente básico de Marx"""

import re
from datetime import datetime
from pathlib import Path
from tkinter import filedialog as fd

MIBILLETERA_MONTHS = (
    "Ene",
    "Feb",
    "Mar",
    "Abr",
    "Mayo",
    "Jun",
    "Jul",
    "Ago",
    "Sep",
    "Oct",
    "Nov",
    "Dic",
)

MIBILLETERA_FILENAME_PATTERN = r"(?P<month>[A-Za-z]+)_(?P<day>\d+)_(?P<year>\d+)_ExpensoDB(?:\.db)?"
PAYCHECK_FILENAME_PATTERN = r"^\d{2}-\d{4}(-X)?\.pdf$"


def validate_path(path: str | Path) -> Path:
    """Verifica que 'path' es una ruta válida

    Si no lo es, muestra un mensaje de error y devuelve el código de error.
    Si 'path' está vacío, lanzará una excepción.

    Convierte 'path' a un objeto 'Path' si no lo es ya.

    """
    if not path:
        raise ValueError("Se ha pasado una ruta vacía a 'validate_path'")
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"No se ha encontrado la ruta '{path}'")
    return path


def most_recent_db(path: Path) -> Path:
    """Devuelve la base de datos más reciente en 'path'

    Los nombres de las bases de datos deben tener el formato por defecto de
    la app de MiBilletera, de lo contrario, serán ignorados. Este formato
    es: 'MMM_DD_YYYY_ExpensoDB', donde 'MMM' es el mes en tres o cuatro
    letras, 'DD' es el día, y 'YYYY' es el año. La fecha formada por estos
    tres elementos será el criterio de ordenación.

    """
    choice = None
    top_date = datetime(1901, 1, 1)
    for file in (p for p in path.iterdir() if p.is_file()):
        match = re.fullmatch(MIBILLETERA_FILENAME_PATTERN, file.stem)
        if not match:
            continue
        month = MIBILLETERA_MONTHS.index(match.group("month")) + 1
        date = datetime(int(match.group("year")), month, int(match.group("day")))
        if date > top_date:
            top_date = date
            choice = file
    if choice is None:
        raise FileNotFoundError(f"No se ha encontrado ninguna base de datos en '{path}'")
    return validate_path(choice)


def most_recent_paycheck(path: Path) -> Path:
    """Devuelve la nómina más reciente en 'path'

    El nombre del archivo de la nómina debe tener format 'MM-YYYY[-X].pdf',
    de lo contario, será ignorado. 'MM' será el mes, 'YYYY' el año, y 'X',
    un caracter especial para indicar nóminas extra. La fecha formada por
    estos tres elementos será el criterio de ordenación.

    """
    choice = None
    top_cmp = (0, 0, 0)
    for file in (p for p in path.iterdir() if p.is_file()):
        match = re.fullmatch(PAYCHECK_FILENAME_PATTERN, file.name)
        if not match:
            continue
        month, year, *extra = file.stem.split("-")
        cmp = (int(month), int(year), 1 if extra else 0)
        if cmp > top_cmp:
            top_cmp = cmp
            choice = file
    if choice is None:
        raise FileNotFoundError(f"No se ha encontrado ningún archivo de nómina en '{path}'")
    return validate_path(choice)


class dialog:
    @staticmethod
    def load(basepath: Path) -> Path:
        """Abre un diálogo para seleccionar un archivo para abrir"""
        path = fd.askopenfilename(
            initialdir=basepath,
            title="Selecciona base de datos",
        )
        return validate_path(path)

    @staticmethod
    def save(basepath: Path) -> Path:
        """Abre un diálogo para seleccionar un archivo para guardar"""
        path = fd.asksaveasfilename(
            initialdir=basepath,
            title="Guardar base de datos",
        )
        Path(path).touch()
        return validate_path(path)


def parse_date(date: str | datetime | None) -> datetime:
    """Convierte 'date' a un objeto 'datetime'"""
    if date is None:
        return datetime.now()
    if isinstance(date, datetime):
        return date
    if all(char.isdigit() for char in date):
        return datetime.strptime(date, "%Y%m%d")
    blocks = []
    block = []
    for char in date:
        if char.isdigit():
            block.append(char)
        else:
            blocks.append("".join(block))
            block = []
    blocks.append("".join(block))
    if not len(blocks) == 3:
        raise ValueError(f"Formato de fecha no reconocido: {date!r}")
    if len(blocks[0]) == 4:
        return datetime.strptime("-".join(blocks), "%Y-%m-%d")
    elif len(blocks[2]) == 4:
        return datetime.strptime("-".join(blocks), "%d-%m-%Y")
    raise ValueError(f"Formato de fecha no reconocido: {date!r}")
