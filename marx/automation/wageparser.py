# Python 3.10.11
# Creado: 25/02/2024
"""Parser para la nómina de sueldos de Telefónica.

Presenta la clase WageParser, que implementa todas las funcionalidades
necesarias para ubicar, leer, procesar y generar los eventos apropiados para la
contabilidad.

"""

import configparser
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from PyPDF2 import PdfReader, PageObject

from marx.model import MarxAdapter


DEFAULT_CFG = Path(__file__).parent.parent.parent / "config" / "wage.cfg"

CONCEPT_LN_PATTERN = r"^(?:\d\d-\d\d|BENEF ).*"
FILENAME_PATTERN = r"\d{2}-\d{4}(-[A-Za-z])?\.pdf"
TOTAL_LN_PATTERN = r"^\*+([0-9]+\.)?[0-9]+,[0-9]+$"

ERROR = "Error parseando nómina:"


class WageParser:
    """Clase para parsear nóminas de sueldos de Telefónica.

    El método principal de esta clase es 'parse', que recibe la ruta de un
    archivo PDF que debe tener nombre y formato de nómina de Telefónica. A
    partir de este archivo, se extraen los datos necesarios para generar los
    eventos apropiados, que se añaden a la base de datos.

    El constructor recibe un adaptador de Marx. También puede recibir la ruta
    del archivo de configuración donde se indique cómo construir los eventos
    a partir de los datos extraídos del PDF.

    """

    def __init__(self, adapter: MarxAdapter, *, cfg_path: str | Path = DEFAULT_CFG):
        self.adapter = adapter
        self.adapter.load()
        self.cfg_path = cfg_path

    # Búsqueda e iteración de archivos

    def iter_all(self, dir: str | Path) -> Iterator[Path]:
        """Itera sobre todos los archivos en el directorio 'dir' que tengan
        formato válido para ser nóminas.

        """
        for item in Path(dir).iterdir():
            if item.is_dir():
                for file in item.iterdir():
                    try:
                        self.parse_filename(file.name)
                    except ValueError:
                        continue
                    yield file
            else:
                try:
                    self.parse_filename(item.name)
                except ValueError:
                    continue
                yield item

    def most_recent(self, dir: str | Path) -> Path:
        """Ubica el archivo más reciente en el directorio 'dir'."""
        choice = None
        top_date = (1901, 1, 1)
        for file in self.iter_all(dir):
            value = self.parse_filename(file.name)
            if value > top_date:
                top_date = value
                choice = file
        if not choice:
            raise FileNotFoundError(f"{ERROR} No se encontró ningún archivo válido.")
        return choice

    def parse_filename(self, filename: str) -> tuple[int, int, int]:
        """Comprueba que el nombre de archivo es válido, y extrae de éste un
        valor de comparación con otros archivos para determinar el más
        reciente.

        """
        match = re.match(FILENAME_PATTERN, filename)
        if not match:
            raise ValueError(f"{ERROR} Nombre de archivo inválido.")
        month, year, *extra = filename.replace(".pdf", "").split("-")
        return (int(year), int(month), 1 if extra else 0)

    def parse(
        self, path: str | Path, *, date: str | datetime | None = None, verbose: bool = False
    ) -> None:
        """Parsea el archivo PDF y añade los eventos a la base de datos.

        Comprueba que el parseo ha sido correcto comparando la suma de los
        resultados individuales con el total a ingresar extraído del PDF.

        Por defecto, los eventos generados llevarán la fecha del día en que se
        ejecuta el método. Si se quiere especificar una fecha distinta, se
        puede hacer mediante el parámetro 'date', que admite un string con el
        formato "YYYY-MM-DD" o un objeto datetime.

        Para mostrar información detallada sobre el proceso de parseo, se puede
        activar el parámetro 'verbose'.

        """
        # Comprobaciones del archivo
        if isinstance(path, str):
            path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"{ERROR} No se encontró el archivo {path!s}")
        _, month, _ = self.parse_filename(path.name)

        # Fecha
        if not date:
            date = datetime.now()
        elif isinstance(date, str):
            date = datetime.strptime(date, "%Y-%m-%d")

        # Cargando configuración
        cfg_events, cfg_extra = self.parse_config()
        match_to_key = {}
        for key, value in cfg_extra.items():
            for match in value["match"]:
                match_to_key[match] = key

        # Lectura del archivo y extracción de datos
        reader = PdfReader(path)
        wage = {key: 0.0 for key in cfg_events}
        irpf = None
        parsed_total = None
        for page in reader.pages:
            partial_wage, new_irpf, new_total = self.parse_page(page, match_to_key)
            for concept, value in partial_wage.items():
                wage[concept] += value
            irpf = irpf or new_irpf
            parsed_total = parsed_total or new_total

        # Comprobaciones
        calc_total = 0.0
        for key, amount in wage.items():
            calc_total += amount * cfg_extra[key]["flow"]
        if abs(calc_total - parsed_total) > 0.02:
            raise ValueError(
                f"{ERROR} La suma de los conceptos no coincide con el total a ingresar:"
                f" calculado = {calc_total:.2f}, extraído = {parsed_total:.2f}"
            )

        # Sustitución de valores dinámicos
        whyextra = "quién sabe"
        if month in (6, 7, 8):
            whyextra = "verano"
        elif month in (11, 12, 1):
            whyextra = "Navidad"
        elif month in (2, 3):
            whyextra = "beneficios"
        changes = {"pct": f"{irpf/100:.2%}".replace(".", ","), "whyextra": whyextra}

        # Creación de eventos
        for key in sorted(cfg_extra, key=lambda k: cfg_extra[k]["order"]):
            amount = wage[key]
            if amount == 0:
                continue
            params = cfg_events[key].copy()
            for param in params:
                if isinstance(params[param], str):
                    for change, new in changes.items():
                        params[param] = params[param].replace(f"${change}$", new)
            params["date"] = date
            params["amount"] = amount
            event = self.adapter.suite.events.new(id=-1, **params)
            if verbose:
                print(f"Evento creado: {event!s} || {event.details}")

    def parse_page(
        self, page: PageObject, match_to_key: dict[str, str]
    ) -> tuple[dict[str, float], float, float]:
        """Extrae los datos de la página del PDF.

        Devuelve un diccionario con las cantidades de los conceptos
        identificados, junto con el porcentaje de IRPF y el total a ingresar.

        """
        text = page.extract_text()

        # % de IRPF de este mes
        irpf = None
        for line in text.split("\n"):
            if irpf:
                irpf = float(line.strip().replace(",", "."))
                break
            irpf = line == "MADRID"

        # Total a ingresar
        total = 0.0
        for line in text.split("\n"):
            if re.match(TOTAL_LN_PATTERN, line):
                total = float(line.strip("*").replace(".", "").replace(",", "."))

        # Procesado de las líneas del PDF
        wage = {key: 0.0 for key in match_to_key.values()}
        for line in re.findall(CONCEPT_LN_PATTERN, text, re.MULTILINE):
            if not ". ." in line:
                raw_value = []
                for char in reversed(line.strip()):
                    if char not in "0123456789,.":
                        break
                    char = char.replace(".", "").replace(",", ".")
                    raw_value.append(char)
                value = float("".join(reversed(raw_value)))
                for match, key in match_to_key.items():
                    if match is None or match in line:
                        wage[key] += value
                        break
        return wage, irpf, total

    def parse_config(self) -> tuple[dict[str, Any], dict[str, Any]]:
        """Parsea el archivo de configuración donde se indica cómo construir
        los eventos a partir de los datos extraídos del PDF.

        Devuelve dos diccionarios: uno sólo con los parámetros necesarios para
        crear cada evento, y otro con parámetros extra que pueden ser útiles
        durante la ejecución del parser.

        """
        parser = configparser.RawConfigParser()
        parser.read(self.cfg_path, encoding="utf-8")
        events = {}
        extra = {}
        for section in parser.sections():
            # Extra
            extra[section] = {}
            try:
                matches = parser.get(section, "match").split(",")
                extra[section]["match"] = [match.strip(" ").strip('"') for match in matches]
            except configparser.NoOptionError:
                if section == "default":
                    extra[section]["match"] = [None]
                else:
                    raise ValueError(f"{ERROR} No se ha especificado 'match' en {section}")
            extra[section]["flow"] = parser.getint(section, "flow", fallback=-1)
            extra[section]["order"] = parser.getint(section, "order", fallback=1000)
            # Eventos
            events[section] = {}
            acc_income = self.adapter.suite.accounts["Ingresos"].entity
            if "orig" not in parser.options(section) and "dest" not in parser.options(section):
                raise ValueError(f"{ERROR} No se ha especificado 'orig' o 'dest' en {section}")
            if "orig" in parser.options(section) and "dest" in parser.options(section):
                raise ValueError(
                    f"{ERROR} No se pueden especificar 'orig' y 'dest' a la vez en {section}"
                )
            if "orig" in parser.options(section):
                events[section]["dest"] = acc_income
                orig = parser.get(section, "orig").strip('"')
                if orig.startswith("@"):
                    events[section]["orig"] = self.adapter.suite.accounts[orig[1:]].entity
                else:
                    events[section]["orig"] = orig
            if "dest" in parser.options(section):
                events[section]["orig"] = acc_income
                dest = parser.get(section, "dest").strip('"')
                if dest.startswith("@"):
                    events[section]["dest"] = self.adapter.suite.accounts[dest[1:]].entity
                else:
                    events[section]["dest"] = dest
            try:
                cat_code = parser.get(section, "category")
                events[section]["category"] = self.adapter.suite.categories[cat_code].entity
            except configparser.NoOptionError:
                raise ValueError(f"{ERROR} No se ha especificado 'category' en {section}")
            try:
                concept = parser.get(section, "concept")
                events[section]["concept"] = concept.strip('"')
            except configparser.NoOptionError:
                raise ValueError(f"{ERROR} No se ha especificado 'concept' en {section}")
            if "details" in parser.options(section):
                events[section]["details"] = parser.get(section, "details", fallback="").strip('"')
        return events, extra

    def _parsing_test(self, path: str | Path):
        """Pruebas de parsing."""
        # Comprobaciones del archivo
        if isinstance(path, str):
            path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"{ERROR} No se encontró el archivo {path!s}")

        # Lectura
        reader = PdfReader(path)
        for page in reader.pages:
            text = page.extract_text()
            for line in text.split("\n"):
                if re.match(r"^\*+([0-9]+\.)?[0-9]+,[0-9]+$", line):
                    print(">>>", line)
        print()
