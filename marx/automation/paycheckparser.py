# Python 3.10.11
# Creado: 31/07/2024
"""Herramienta para extracción automatizada de los datos de una nómina

Presenta la clase 'PaycheckParser', que permite interpretar y extraer los datos
relevantes de una nómina, y transformarlos en eventos de acuerdo a una serie
de reglas definidas en archivos TOML llamados "criterios".

"""

import math
import re
from datetime import datetime
from collections import defaultdict
from pathlib import Path

import toml
from PyPDF2 import PdfReader, PageObject

from marx.models import Event, MarxDataStruct
from marx.util.factory import Factory


FILENAME_PATTERN = r"\d{2}-\d{4}(-[A-Za-z])?\.pdf"
LN_ELEMENT_PATTERN = r"^(?:\d\d-\d\d|BENEF ).*"
LN_TOTAL_PATTERN = r"^\*+([0-9]+\.)?[0-9]+,[0-9]+$"

PH_IRPF = "%pct%"
PH_EXTRA_OCCASION = "%occasion%"

DEFAULT = "_default_"


def esp2iso(text: str) -> str:
    """Convierte una cadena de texto con un valor flotante con formato español
    a formato ISO"""
    return text.strip().replace(".", "").replace(",", ".")


class PaycheckParser:
    """Parser de nóminas

    Actúa como una interfaz que expone el método 'parse', con el que se extrae
    la información de una nómina con formato PDF.

    El constructor recibe la estructura de datos Marx que se esté usando, y la
    ruta al archivo TOML con los criterios de extracción y generación de
    eventos. A su vez, el método 'parse' debe recibir la ruta al archivo PDF
    con la nómina a analizar, y también la fecha en la que se deben imputar
    los eventos generados.

    """

    def __init__(self, data: MarxDataStruct, criteria: Path):
        self.data = data

        # Cargar los criterios de extracción
        criteria = toml.load(criteria)
        defaults = {key: value for key, value in criteria.items() if not isinstance(value, dict)}
        self.criteria = {
            key: {**defaults, **value} for key, value in criteria.items() if isinstance(value, dict)
        }

        # Comprobar que los criterios son válidos
        for key, params in self.criteria.items():
            if key != DEFAULT and not "match" in params:
                raise ValueError(f"[PaycheckParser] El criterio {key!r} no tiene parámetro 'match'")
            if key == DEFAULT and "match" in params:
                raise ValueError(
                    "[PaycheckParser] El criterio por defecto no puede tener parámetro 'match'"
                )
            if "category" not in params:
                raise ValueError(
                    f"[PaycheckParser] El criterio {key!r} no tiene parámetro 'category'"
                )
            if "orig" not in params and "dest" not in params:
                raise ValueError(
                    f"[PaycheckParser] El criterio {key!r} no tiene parámetro 'orig' o 'dest'"
                )
            if "orig" in params and "dest" in params:
                raise ValueError(
                    f"[PaycheckParser] El criterio {key!r} no puede tener parámetros 'orig' y 'dest'"
                )
            if "order" not in params:
                params["order"] = 1000

    def parse(self, paycheck: Path, date: datetime) -> Factory[Event]:
        """Extrae la información de una nómina

        Se extrae la información de una nómina con formato PDF, generando
        eventos en función de los criterios definidos en el archivo TOML.

        Devuelve la lista de eventos generados que, además, se añaden a la
        estructura de datos Marx.

        """
        reader = PdfReader(paycheck)

        # Cantidades de cada componente definido en los criterios
        totals = {key: 0.0 for key in self.criteria}
        for page in reader.pages:
            for key, value in self._parse_page(page).items():
                if key in totals:
                    totals[key] += value

        # % de IRPF y total a ingresar según la nómina
        irpf_pct = False
        total = 0.0
        for page in reader.pages:
            for line in page.extract_text().split("\n"):
                # % de IRPF
                if irpf_pct is True:
                    irpf_pct = float(esp2iso(line))
                elif irpf_pct is False:
                    irpf_pct = line == "MADRID"
                # Total a ingresar
                if re.match(LN_TOTAL_PATTERN, line):
                    total = float(esp2iso(line.strip("*")))

        # Comprobación de que la extracción es correcta
        calc_total = 0.0
        for key, value in totals.items():
            params = self.criteria[key]
            if params["category"].startswith("A"):
                calc_total += value
            elif params["category"].startswith("B"):
                calc_total -= value
            elif params["category"].startswith("T"):
                if "orig" in params:
                    calc_total += value
                if "dest" in params:
                    calc_total -= value
        if not math.isclose(calc_total, total, rel_tol=1e-3):
            raise ValueError(
                f"[PaycheckParser] La suma de los componentes extraídos ({calc_total}) "
                f"no coincide con el total a ingresar ({total})"
            )

        # Orden en el que se generan los eventos
        sorted_keys = sorted(self.criteria, key=lambda key: self.criteria[key]["order"])

        # Generación de eventos
        paycheck_account = self.data.accounts.subset(name="Ingresos").pullone()
        events = self.data.events.subset()
        for key in sorted_keys:
            value = totals[key]
            if value == 0.0:
                continue
            params = self.criteria[key]
            category = self.data.categories.subset(code=params["category"]).pullone()
            if category is None:
                raise ValueError(
                    f"[PaycheckParser] No se encuentra la categoría {params['category']!r}"
                )
            if "orig" in params:
                dest = paycheck_account
                orig = params["orig"]
                if orig.startswith("@"):
                    orig = self.data.accounts.subset(repr_name=params["orig"]).pullone()
                    if orig is None:
                        raise ValueError(
                            f"[PaycheckParser] No se encuentra la cuenta {params['orig']!r}"
                        )
            if "dest" in params:
                orig = paycheck_account
                dest = params["dest"]
                if dest.startswith("@"):
                    dest = self.data.accounts.subset(repr_name=params["dest"]).pullone()
                    if dest is None:
                        raise ValueError(
                            f"[PaycheckParser] No se encuentra la cuenta {params['dest']!r}"
                        )
            for info_param in ("concept", "details"):
                if info_param not in params:
                    continue
                if PH_IRPF in params[info_param]:
                    str_irpf_pct = f"{irpf_pct/100:.2%}".replace(".", ",")
                    params[info_param] = params[info_param].replace(PH_IRPF, str_irpf_pct)
                if PH_EXTRA_OCCASION in params[info_param]:
                    month = self._extract_month(paycheck)
                    occasion = (
                        "verano"
                        if month in (6, 7, 8)
                        else (
                            "Navidad"
                            if month in (11, 12, 1)
                            else "beneficios" if month in (2, 3) else "extras"
                        )
                    )
                    params[info_param] = params[info_param].replace(PH_EXTRA_OCCASION, occasion)
            event = self.data.events.new(
                -1,
                date=date,
                amount=round(value, 2),
                category=category,
                orig=orig,
                dest=dest,
                concept=params.get("concept", ""),
                details=params.get("details", ""),
            )
            events.join(event)

        return events

    def _parse_page(self, page: PageObject) -> dict[str, float]:
        """Parsea una página

        Utiliza los 'match' definidos en los criterios para asignar el valor
        extraído a la clave correspondiente.

        """
        text = page.extract_text()
        res = defaultdict(float)
        for line in re.findall(LN_ELEMENT_PATTERN, text, re.MULTILINE):
            if ". ." in line:
                continue
            # Extraer el valor
            raw_value = []
            for char in reversed(line.strip()):
                if char not in "0123456789,.":
                    break
                raw_value.append(esp2iso(char))
            value = float("".join(reversed(raw_value)))
            # Asignar el valor a la clave correspondiente
            for key, params in self.criteria.items():
                matches = params.get("match", None)
                matches = [matches] if isinstance(matches, str) else matches
                if not matches:
                    continue
                if any(match in line for match in matches):
                    res[key] += value
                    break
            else:
                res[DEFAULT] += value
        return res

    def _extract_month(self, paycheck: Path) -> int:
        """Extrae el mes de un archivo de nómina"""
        month, year, *_ = paycheck.stem.split("-")
        return int(month)
