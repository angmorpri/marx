# Python 3.10.11
# Creado: 31/01/2024
"""Utilidades varias."""

import configparser
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


def parse_auto_cfg(path: str | Path) -> dict[str, str]:
    """Lee el archivo de configuración automática y devuelve un diccionario."""
    ERROR = "Error parseando el archivo de configuración:"
    parser = configparser.RawConfigParser()
    parser.read(path, encoding="utf-8")
    base_sink = {}
    for section in parser.sections():
        if section == "source":
            try:
                source = parser.get(section, "target")
            except configparser.NoOptionError:
                raise ValueError(f"{ERROR} No se ha especificado la fuente de datos")
            amount = parser.getfloat(section, "amount", fallback=None)
            ratio = parser.getfloat(section, "ratio", fallback=None)
        elif section == "sinks":
            # Valor por defecto para todos los sinks
            for option in parser.options(section):
                if option in ("amount", "ratio"):
                    base_sink[option] = parser.getfloat(section, option)
                else:
                    base_sink[option] = parser.get(section, option)
    sinks = []
    for section in parser.sections():
        if section.startswith("sinks."):
            sink = base_sink.copy()
            sink["sid"] = sid = section.split(".")[1]
            for key in ("amount", "ratio", "details", "target", "category", "concept"):
                if key in sink:
                    continue
                try:
                    if key in ("amount", "ratio"):
                        sink[key] = parser.getfloat(section, key)
                    else:
                        sink[key] = parser.get(section, key).strip('"')
                except configparser.NoOptionError:
                    if key in ("target", "category", "concept"):
                        raise ValueError(
                            f"{ERROR} No se ha especificado {key} obligatoria en sumidero {sid}"
                        )
                    else:
                        pass
            sinks.append(sink)
    return source, amount, ratio, sinks


if __name__ == "__main__":
    cfgpath = Path(__file__).parent.parent / "config" / "autoq.cfg"
    print(parse_auto_cfg(cfgpath))
