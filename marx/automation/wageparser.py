# Python 3.10.11
# Creado: 25/02/2024
"""Parser para la nómina de sueldos de Telefónica.

Presenta la clase WageParser, que implementa todas las funcionalidades
necesarias para ubicar, leer, procesar y generar los eventos apropiados para la
contabilidad.

"""

import configparser
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from PyPDF2 import PdfReader, PageObject

from marx.model import MarxAdapter


DEFAULT_CFG = Path(__file__).parent.parent.parent / "config" / "wage.cfg"

FILENAME_PATTERN = r"\d{2}-\{4}(-[A-Za-z])?\.pdf"
CONCEPT_LN_PATTERN = r"^(?:\d\d-\d\d|BENEF ).*"

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

    def most_recent(self, dir: str | Path) -> Path:
        """Ubica el archivo más reciente en el directorio 'dir'."""
        current_value = (0, 0, 0)
        winner = None
        for item in Path(dir).iterdir():
            if item.is_dir():
                for file in item.iterdir():
                    try:
                        value = self.parse_filename(file.name)
                    except ValueError:
                        continue
            else:
                try:
                    value = self.parse_filename(item.name)
                except ValueError:
                    continue
            if value > current_value:
                current_value = value
                winner = item
        if not winner:
            raise FileNotFoundError(f"{ERROR} No se encontró ningún archivo válido.")
        return winner

    def parse_filename(self, filename: str) -> tuple[int, int, int]:
        """Comprueba que el nombre de archivo es válido, y extrae de éste un
        valor de comparación con otros archivos para determinar el más
        reciente.

        """
        match = re.fullmatch(FILENAME_PATTERN, filename)
        if not match:
            raise ValueError(f"{ERROR} Nombre de archivo inválido.")
        month, year, *extra = filename.stem.split("-")
        return (int(year), int(month), 1 if extra else 0)

    def parse(self, path: str | Path) -> None:
        """Parsea el archivo PDF y añade los eventos a la base de datos."""
        # Comprobaciones del archivo
        if isinstance(path, str):
            path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"{ERROR} No se encontró el archivo {path!s}")
        y, m, x = self.parse_filename(path.name)

        # Lectura del archivo y extracción de datos
        reader = PdfReader(path)
        wage = defaultdict(float)
        for page in reader.pages:
            partial_wage, irpf = self.parse_page(page)
            for concept, value in partial_wage.items():
                wage[concept] += value

        # [TEST] Mostrar resultados
        print(f"Fecha: {y}-{m:02d} ({'extra' if x else 'normal'})")
        for concept, value in wage.items():
            print(f"+ {concept}: {value}")
        print(f"IRPF: {irpf}")

    def parse_page(self, page: PageObject) -> tuple[defaultdict, float]:
        """Extrae los datos de la página del PDF."""
        text = page.extract_text()

        # % de IRPF de este mes
        irpf = None
        for line in text.split("\n"):
            if irpf:
                irpf = float(line.strip().replace(",", "."))
                break
            irpf = line == "MADRID"

        # Conceptos y valores

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
                extra[section]["match"] = parser.get(section, "match")
            except configparser.NoOptionError:
                if section == "default":
                    extra[section]["match"] = None
                else:
                    raise ValueError(f"{ERROR} No se ha especificado 'match' en {section}")
            extra[section]["flow"] = parser.getint(section, "flow", fallback=-1)
            # Eventos
            events[section] = {}
            acc_income = self.adapter.suite.accounts["Ingresos"].entity
            if "details" not in parser.options(section):
                events[section]["details"] = ""
            if "orig" not in parser.options(section) and "dest" not in parser.options(section):
                raise ValueError(f"{ERROR} No se ha especificado 'orig' o 'dest' en {section}")
            if "orig" in parser.options(section) and "dest" in parser.options(section):
                raise ValueError(
                    f"{ERROR} No se pueden especificar 'orig' y 'dest' a la vez en {section}"
                )
            if "orig" in parser.options(section):
                events[section]["dest"] = acc_income
            if "dest" in parser.options(section):
                events[section]["orig"] = acc_income
