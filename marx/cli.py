# Python 3.10.11
# Creado: 28/06/2024
"""Cliente por defecto para Marx

Presenta la clase 'MarxCLI', que se puede instanciar para interactuar con la
API de Marx desde la línea de comandos. Tiene dos modos de ejecución: si se le
pasan argumentos, los ejecutará sobre la API directamente y devolverá el
resultado; si no, se abrirá un intérprete interactivo.

"""

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from tkinter import filedialog as fd
from typing import Any

import toml

from marx import Marx


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

    def get(self, key: str) -> Any:
        """Devuelve el valor de la clave 'key', en cualquier sección del
        archivo de configuración

        Si no la encuentra, lanzará un KeyError.

        Las claves terminadas en '_dir' o '_path' serán convertidas a objetos
        'Path' automáticamente.

        """
        for field, value in self.config.items():
            if isinstance(value, dict):
                if key in value:
                    return self._convert(key, value[key])
            elif field == key:
                return self._convert(key, value)
        raise KeyError(
            f"[UserConfig] La clave {key!r} no se ha encontrado en el archivo de configuración de usuario"
        )

    def _convert(self, key: str, value: Any) -> Any:
        """Convierte automáticamente 'value' si es posible"""
        if not value:
            raise ValueError(f"[UserConfig] La clave '{key}' existe, pero no tiene valor")
        if key.endswith("_dir") or key.endswith("_path"):
            return Path(value)
        return value


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
        return self.validate_path(path)

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
        if isinstance(key, Path):
            path = key
            if not path.is_absolute():
                path = self.userconfig.get("databases_dir") / key
        elif key in ("auto", "pick"):
            path = self.userconfig.get("databases_dir")
        elif os.path.isabs(key):
            path = Path(key)
        else:
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
        partir de la original. Si 'key' es None o 'auto', se escogerá un nombre
        seguro automáticamente, en el mismo directorio que la base de datos
        original. Si es 'pick', se abrirá una ventana de diálogo para elegir un
        nombre. En caso contrario, si es un nombre de fichero, se guardará en
        la misma dirección que la base de datos original, y si es una ruta
        completa, se usará directamente.

        """
        raise NotImplementedError

    def autoquotas(self, date: str | datetime | None = None) -> None:
        """Distribuye automáticamente las cuotas mensuales

        Utiliza el archivo de criterios especificado en la configuración de
        usuario. 'date' es la fecha en la que se imputarán las cuotas; si es
        None, usará la fecha actual; si es una cadena de caracteres, tendrá que
        tener formato 'YYYY-MM-DD' o 'DD-MM-YYYY', teniendo en
        cuenta que '-' puede ser cualquier caracter no alfanumérico, o incluso
        ninguno.

        """
        raise NotImplementedError

    def autoinvest(self, date: str | datetime | None = None) -> None:
        """Distribuye automáticamente inversiones

        Utiliza el archivo de criterios especificado en la configuración de
        usuario. 'date' es la fecha en la que se imputarán las cuotas; si es
        None, usará la fecha actual; si es una cadena de caracteres, tendrá que
        tener formato 'YYYY-MM-DD' o 'DD-MM-YYYY', teniendo en
        cuenta que '-' puede ser cualquier caracter no alfanumérico, o incluso
        ninguno.

        """
        raise NotImplementedError

    def distr(self, criteria_path: str | Path, date: str | datetime | None = None) -> None:
        """Distribuye automáticamente según el archivo de criterios indicado
        en 'criteria_path'

        'date' es la fecha en la que se imputarán las cuotas; si es None, usará
        la fecha actual; si es una cadena de caracteres, tendrá que tener
        formato 'YYYY-MM-DD' o 'DD-MM-YYYY', teniendo en cuenta que '-' puede
        ser cualquier caracter no alfanumérico, o incluso ninguno.

        """
        raise NotImplementedError

    def paycheck(
        self,
        paycheck_path: str | Path | None,
        criteria_path: str | Path | None,
        date: str | datetime | None = None,
    ) -> None:
        """Distribuye automáticamente según el archivo de nómina indicado en
        'paycheck_path' y el archivo de criterios indicado en 'criteria_path'

        Si 'paycheck_path' no se indica, se utilizará el que aparezca en la
        configuración de usuario; lo mismo para 'criteria_path'. 'date' es la
        fecha en la que se imputarán las cuotas; si es None, usará la fecha
        actual; si es una cadena de caracteres, tendrá que tener formato
        'YYYY-MM-DD' o 'DD-MM-YYYY', teniendo en cuenta que '-' puede ser
        cualquier caracter no alfanumérico, o incluso ninguno.

        """
        raise NotImplementedError

    def loans_list(self, date: str | datetime | None = None) -> None:
        """Identifica y muestra los préstamos y deudas pendientes

        'date' es la fecha hasta la que se buscan ambos conceptos; si es None,
        usará la fecha actual; si es una cadena de caracteres, tendrá que tener
        formato 'YYYY-MM-DD' o 'DD-MM-YYYY', teniendo en cuenta que '-' puede
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
