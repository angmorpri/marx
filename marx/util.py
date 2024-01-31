# Python 3.10.11
# Creado: 31/01/2024
"""Utilidades varias."""

import re
from datetime import datetime
from pathlib import Path


MYWALLET_MONTHS = (
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


def get_most_recent_db(db_dir: str | Path, *, allow_prefixes: bool = True) -> Path:
    """Devuelve la ruta del archivo más reciente disponible en 'db_dir'.

    Para determinar el archivo más reciente, usará el formato de nombres de
    las bases de datos de MiBilletera, esto es:

        [<prefijo>_]<mes>_<día>_<año>_ExpensoDB[.db]

    Donde <prefijo> puede ser cualquier cadena de caracteres. Si no se
    quiere admitir prefijos, se puede indicar mediante el parámetro
    'allow_prefixes'.

    Si no se hallan archivos válidos en la ruta indicada, se lanza un
    FileNotFoundError.

    """
    path = Path(db_dir)
    pattern = r"(?:(?P<prefix>[^\s]+)_)?(?P<month>[A-Za-z]+)_(?P<day>\d+)_(?P<year>\d+)_ExpensoDB(?:\.db)?"
    choice = None
    top_date = datetime(1901, 1, 1)
    for file in (p for p in path.iterdir() if p.is_file()):
        match = re.fullmatch(pattern, file.stem)
        if not match:
            continue
        if not allow_prefixes and match.group("prefix"):
            continue
        month = MYWALLET_MONTHS.index(match.group("month")) + 1
        date = datetime(int(match.group("year")), month, int(match.group("day")))
        if date > top_date:
            top_date = date
            choice = file
    if not choice:
        raise FileNotFoundError("No se encontró ninguna base de datos válida")
    return choice
