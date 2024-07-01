# Python 3.10.11
# Creado: 31/01/2024
"""Utilidades varias."""

import configparser
import re
from datetime import datetime
from pathlib import Path
from pprint import pprint
from typing import Any


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


def parse_nested_cfg(path: str | Path) -> dict[str, Any]:
    """Lee un archivo de configuración con jerarquías y devuelve el diccionario
    equivalente.

    Un archivo de configuración jerarquías es aquel en el que las secciones
    pueden tomar la forma "[<parent>.<child>]", de tal manera que todos los
    <child> serán subsecciones de <parent>. Además, los valores que aparezcan
    en una sección "[<parent>]" a secas, serán heredados por todas las
    subsecciones (y también aparecerán en una clave auxiliar "__defaults__").

    Devuelve un diccionario con todas las claves pertinentes.

    """

    def clean(d: dict) -> dict:
        """Pasa dígitos a enteros o flotantes y elimina comillas."""
        cleaned = {}
        for key, value in d.items():
            if not isinstance(value, str):
                cleaned[key] = value
                continue
            try:
                cleaned[key] = float(value)
            except ValueError:
                cleaned[key] = value.strip('"').strip("'").strip()
        return cleaned

    parser = configparser.RawConfigParser()
    parser.read(path, encoding="utf-8")
    parents = []
    for section in parser.sections():
        as_parent = f"{section}."
        if any(s.startswith(as_parent) for s in parser.sections()):
            parents.append(section)
    res = {}
    for section in sorted(parser.sections(), key=lambda x: x.count(".")):
        if "." in section:
            *path, target = section.split(".")
            subset = res
            for key in path:
                if key not in subset:
                    subset[key] = {}
                subset = subset[key]
        else:
            target = section
            subset = res
        defaults = subset.get("__defaults__", {}).copy()
        if section in parents:
            subset[target] = {"__defaults__": defaults}
            subset[target]["__defaults__"].update(clean(parser[section]))
        else:
            subset[target] = defaults
            subset[target].update(clean(parser[section]))
    return res


if __name__ == "__main__":
    cfgpath = Path(__file__).parent.parent.parent / "config" / "wageparser.cfg"
    res = parse_nested_cfg(cfgpath)

    pprint(res)
