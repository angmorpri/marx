# Python 3.10.11
# Creado: 28/06/2024
"""Cliente por defecto para Marx

Presenta la clase 'MarxCLI', que se puede instanciar para interactuar con la
API de Marx desde la línea de comandos. Tiene dos modos de ejecución: si se le
pasan argumentos, los ejecutará sobre la API directamente y devolverá el
resultado; si no, se abrirá un intérprete interactivo.

"""

import argparse
from asyncio import events
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from tkinter import filedialog as fd
from typing import Any

import toml

from marx import Marx
from marx.util import safely_rename_file


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


class UserConfig:
    """Clase auxiliar para gestionar la configuración de usuario

    Presenta el método 'get', que devuelve el valor de una clave especificada,
    lanzando un error en caso de no encontrarla. Además, es relativamente
    inteligente, convirtiendo automática el formato de los valores cuando es
    posible.

    El constructor recibe la ruta del archivo de configuración, que debe tener
    formato TOML.

    """

    def __init__(self, path: Path) -> None:
        self.path = path
        if not path.exists():
            raise FileNotFoundError(f"[UserConfig] Archivo no encontrado: {path}")
        self.config = toml.load(path)

    def get(self, key: str, *, safe: bool = True) -> Any:
        """Devuelve el valor de la clave 'key', en cualquier sección del
        archivo de configuración

        Por defecto, si no encuentra la clave, o está vacía, lanzará una
        excepción. Esto se puede evitar pasando 'safe' a False, lo que
        provocará que devuelva None en estos casos.

        Las claves terminadas en '_dir' o '_path' serán convertidas a objetos
        'Path' automáticamente.

        """
        res = None
        for field, value in self.config.items():
            if isinstance(value, dict):
                if key in value:
                    res = value[key]
                    break
            elif field == key:
                res = value
                break
        # no se encuentra o está vacía
        if not res:
            if safe:
                raise KeyError(
                    f"[UserConfig] La clave requerida {key!r} no se encuentra o está vacía"
                )
            return None
        # cast
        if key.endswith("_dir") or key.endswith("_path"):
            return Path(res)
        return res


class MarxCLI:
    """Cliente simple para Marx"""

    def __init__(self, userconfig_path: str | Path) -> None:
        self.marx = Marx()
        self.userconfig = UserConfig(Path(userconfig_path))

    # Métodos de ayuda interna

    def validate_path(self, path: str | Path) -> Path:
        """Verifica que 'path' es una ruta válida"""
        if not path:
            raise ValueError("[MarxCLI] Ruta no especificada")
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"[MarxCLI] Ruta no encontrada: {path}")
        return path

    def most_recent_db(self, path: Path) -> Path:
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
        return self.validate_path(choice)

    def most_recent_paycheck(self, path: Path) -> Path:
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
        return self.validate_path(choice)

    def dialog_load(self, basepath: Path) -> Path:
        """Abre un diálogo para seleccionar un archivo para abrir"""
        path = fd.askopenfilename(
            initialdir=basepath,
            title="Selecciona base de datos",
        )
        return self.validate_path(path)

    def dialog_save(self, basepath: Path) -> Path:
        """Abre un diálogo para seleccionar un archivo para guardar"""
        path = fd.asksaveasfilename(
            initialdir=basepath,
            title="Guardar base de datos",
        )
        Path(path).touch()
        return self.validate_path(path)

    def parse_date(self, date: str | datetime | None) -> datetime:
        """Convierte 'date' a un objeto 'datetime'"""
        if date is None:
            return datetime.now()
        if isinstance(date, datetime):
            return date
        if not isinstance(date, str):
            raise TypeError(f"[MarxCLI] Formato de fecha no válida: {date!r}")
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
            raise ValueError(f"[MarxCLI] Formato de fecha no válida: {date!r}")
        if len(blocks[0]) == 4:
            return datetime.strptime("-".join(blocks), "%Y-%m-%d")
        elif len(blocks[2]) == 4:
            return datetime.strptime("-".join(blocks), "%d-%m-%Y")
        raise ValueError(f"[MarxCLI] Formato de fecha no válida: {date!r}")

    def format_event(self, event: dict) -> str:
        """Formatea un evento para mostrarlo por pantalla"""
        id = "----" if event["id"] == -1 else f"{event['id']:04d}"
        sign = "+" if event["flow"] == 1 else "-" if event["flow"] == -1 else "="
        amount = f"{sign} {event['amount']:8.2f} €"
        shconcept = event["concept"]
        if len(shconcept) > 20:
            shconcept = f"{shconcept[:17]}..."
        status = "OPEN" if event["status"] == 0 else "CLOSED"
        rsource = "" if event["rsource"] == -1 else f" RSOURCE {event['rsource']}"
        catcode = event["category"]["code"]
        orig = event["orig"]["repr_name"]
        dest = event["dest"]["repr_name"]
        return f"[{id}] {amount} {event['date']} {shconcept!r} - [{catcode}] {orig} -> {dest} ({status}{rsource})"

    # Adaptadores de la API de Marx

    def load(self, key: str | Path | None = None) -> None:
        """Cargar una base de datos de Marx

        Si 'key' es None o 'auto', usará la que se especifique en el archivo de
        configuración de usuario. Si es 'pick', lanzará una ventana de diálogo
        para seleccionar un archivo. En caso contrario, si es un nombre de
        fichero, lo buscará en la dirección especificada en el archivo de
        configuración de usuario, y si es una ruta completa, tratará de usarla
        directamente.

        Se puede consultar la base de datos actualmente en uso con el comando
        'current'.

        """
        key = key or "auto"
        if key in ("auto", "pick"):
            path = self.userconfig.get("databases_dir")
        else:
            path = Path(key)
            if not path.is_absolute():
                path = self.userconfig.get("databases_dir") / key
        # Verificar que la ruta es válida
        path = self.validate_path(path)
        # Cargar la base de datos
        if key == "auto":
            path = self.most_recent_db(path)
        elif key == "pick":
            path = self.dialog_load(path)
        if not path.is_file():
            raise FileNotFoundError(
                f"[MarxCLI] La ruta proporcionada '{path}' no es un archivo de base de datos"
            )
        self.marx.load(path)
        print(f"Se ha cargado la base de datos en la ruta '{path}'")

    def save(self, key: str | Path | None = None) -> None:
        """Guardar la base de datos actual de Marx

        Siempre se guardan los cambios en una nueva base de datos, formada a
        partir de la original. Si 'key' es None o 'auto', no se modificará el
        nombre que por defecto le asigna la API a la nueva base de datos;
        excepto si se especifica uno diferente en el parámetro
        'default_save_prefix' del archivo de configuración de usuario. Si es
        'pick', se abrirá una ventana de diálogo para elegir un nombre. En caso
        contrario, si es un nombre de fichero, se guardará en la misma
        dirección que la base de datos original, y si es una ruta completa, se
        usará directamente.

        En caso de usar una ruta relativa o absoluta, se puede usar el
        comodín '?', que se sustituirá por el nombre de original de la base de
        datos.

        """
        default_path = self.marx.save()
        source_name = default_path.name.split("_", 1)[1]
        # auto
        if not key or key == "auto":
            default_prefix = self.userconfig.get("default_save_prefix", safe=False)
            if default_prefix:
                clean_path = default_path.parent / source_name
                new_path = safely_rename_file(clean_path, default_prefix)
            else:
                new_path = default_path
        # pick
        elif key == "pick":
            new_path = self.dialog_save(default_path.parent)
        # else
        else:
            new_path = Path(key)
            if not new_path.is_absolute():
                new_path = default_path.parent / key
        # reemplazar comodín
        if "?" in new_path.name:
            new_path = new_path.with_name(new_path.name.replace("?", source_name))
        # reemplazar antiguo archivo por nuevo
        default_path.replace(new_path)
        # validar
        new_path = self.validate_path(new_path)
        print(f"Se ha guardado la base de datos en la ruta '{new_path}'")

    def autoquotas(self, date: str | datetime | None = None) -> None:
        """Distribuye automáticamente las cuotas mensuales

        Utiliza el archivo de criterios especificado en la configuración de
        usuario. 'date' es la fecha en la que se imputarán las cuotas; si es
        None, usará la fecha actual; si es una cadena de caracteres, tendrá que
        tener formato 'YYYYMMDD', 'YYYY-MM-DD' o 'DD-MM-YYYY', teniendo en
        cuenta que '-' puede ser cualquier caracter no alfanumérico, o incluso
        ninguno.

        """
        criteria = self.userconfig.get("autoquotas_criteria_path")
        self.distr(criteria, date)

    def autoinvest(self, date: str | datetime | None = None) -> None:
        """Distribuye automáticamente inversiones

        Utiliza el archivo de criterios especificado en la configuración de
        usuario. 'date' es la fecha en la que se imputarán las cuotas; si es
        None, usará la fecha actual; si es una cadena de caracteres, tendrá que
        tener formato 'YYYYMMDD', 'YYYY-MM-DD' o 'DD-MM-YYYY', teniendo en
        cuenta que '-' puede ser cualquier caracter no alfanumérico, o incluso
        ninguno.

        """
        criteria = self.userconfig.get("autoinvest_criteria_path")
        self.distr(criteria, date)

    def distr(self, criteria_path: str | Path, date: str | datetime | None = None) -> None:
        """Distribuye automáticamente según el archivo de criterios indicado
        en 'criteria_path'

        'date' es la fecha en la que se imputarán las cuotas; si es None, usará
        la fecha actual; si es una cadena de caracteres, tendrá que tener
        formato 'YYYYMMDD', 'YYYY-MM-DD' o 'DD-MM-YYYY', teniendo en cuenta que '-' puede
        ser cualquier caracter no alfanumérico, o incluso ninguno.

        """
        date = self.parse_date(date)
        criteria_path = self.validate_path(criteria_path)
        res = self.marx.distr(criteria_path, date)
        print("Distribución realizada con éxito")
        events_date = res["events"][-1]["date"]
        print(f"Eventos generados para fecha {events_date}:")
        for event in res["events"]:
            catcode = event["category"]["code"]
            orig = event["orig"]["repr_name"]
            dest = event["dest"]["repr_name"]
            print(
                f" > {event['amount']:8.2f} € [{catcode}] ({orig} -> {dest}) {event['concept']!r}"
            )
        print()

    def paycheck(
        self,
        paycheck_path: str | Path | None = None,
        criteria_path: str | Path | None = None,
        date: str | datetime | None = None,
    ) -> None:
        """Distribuye automáticamente según el archivo de nómina indicado en
        'paycheck_path' y el archivo de criterios indicado en 'criteria_path'

        Si 'paycheck_path' es una ruta relativa, se buscará a partir del
        directorio indicado en el archivo de configuración ('paychecks_dir').
        Si 'paycheck_path' no se indica, se utilizará el archivo de nómina más
        reciente del directorio indicado en la configuración de usuario.
        Si 'criteria_path' no se indica, se utilizará la ruta que aparezca en
        el archivo de configuración de usuario ('paycheckparser_criteria_path')

        'date' es la fecha en la que se imputarán las cuotas; si es None, usará
        la fecha actual; si es una cadena de caracteres, tendrá que tener
        formato 'YYYY-MM-DD' o 'DD-MM-YYYY', teniendo en cuenta que '-' puede
        ser cualquier caracter no alfanumérico, o incluso ninguno.

        """
        # date
        date = self.parse_date(date)
        # criteria
        if not criteria_path:
            criteria_path = self.userconfig.get("paycheckparser_criteria_path")
            criteria_path = self.validate_path(criteria_path)
        # paycheck
        if not paycheck_path:
            paychecks_dir = self.userconfig.get("paychecks_dir")
            paycheck_path = self.most_recent_paycheck(paychecks_dir)
        else:
            paycheck_path = Path(paycheck_path)
            if not paycheck_path.is_absolute():
                paychecks_dir = self.userconfig.get("paychecks_dir")
                paycheck_path = paychecks_dir / paycheck_path
        paycheck_path = self.validate_path(paycheck_path)
        # distribución
        res = self.marx.paycheck_parse(paycheck_path, criteria_path, date)
        print("Distribución realizada con éxito")
        events_date = res["events"][-1]["date"]
        print(f"Eventos generados para fecha {events_date}:")
        for event in res["events"]:
            sign = "+" if event["flow"] == 1 else "-" if event["flow"] == -1 else "="
            catcode = event["category"]["code"]
            orig2dest = f"({event['orig']['repr_name']: <12} -> {event['dest']['repr_name']})"
            print(
                f" {sign}{event['amount']:8.2f} € [{catcode}] {orig2dest: <38} {event['concept']!r}"
            )
        print()

    def loans_list(self, date: str | datetime | None = None) -> None:
        """Identifica y muestra los préstamos y deudas pendientes

        'date' es la fecha hasta la que se buscan ambos conceptos; si es None,
        usará la fecha actual; si es una cadena de caracteres, tendrá que tener
        formato 'YYYYMMDD', 'YYYY-MM-DD' o 'DD-MM-YYYY', teniendo en cuenta que '-' puede
        ser cualquier caracter no alfanumérico, o incluso ninguno.

        """
        raise NotImplementedError

    def loans_default(self, tag: str) -> None:
        """Marca un préstamo o deuda identificado con la etiqueta 'tag' como
        default

        """
        raise NotImplementedError

    # Métodos de la interfaz de usuario

    def setup(self) -> None:
        """Configura los comandos y opciones de la interfaz de usuario"""
        self.parser = argparse.ArgumentParser(description="Interfaz de usuario para Marx")
        subparsers = self.parser.add_subparsers(required=True)

        # Comando 'load'
        load_parser = subparsers.add_parser(
            "load", aliases=["l"], help="Cargar una base de datos de Marx"
        )
        load_parser.add_argument(
            "key", nargs="?", help="Modo de carga o ruta de la base de datos a cargar"
        )
        load_parser.set_defaults(func=self.load)
