# Python 3.10.11
# Creado: 25/03/2024
"""API de Marx.

Define la clase "MarxAPI", que se puede instanciar para interactuar con todas
las herramientas del programa.

"""

import configparser
import shutil
from datetime import datetime
from pathlib import Path

from marx.automation import Distribution
from marx.model import MarxAdapter
from marx.util import get_most_recent_db, parse_nested_cfg


PATHS_CFG_FILE = Path(__file__).parent.parent / "config" / "paths.cfg"


class MarxAPI:
    """API de Marx.

    Se presentan las siguientes funciones:

    - update_source: actualiza la fuente utilizada a la más actual.
    - save: guarda los datos modificados.

    - autoquotas: ejecuta el reparto de cuotas mensuales.
    - autoinvest: ejecuta el reparto de inversiones mensuales.
    - autowageparser: ejecuta el parser para nóminas.

    - balance: genera un balance para ciertas fechas.

    - set_path: modifica el directorio o archivo usado por defecto para fuentes
        de datos o configuraciones.
    - copy_config: copia una configuración en un nuevo archivo para que sea
        modificado por el usuario.

    El constructor no recibe argumentos.

    """

    def __init__(self) -> None:
        # Carga directorios y archivos de configuración.
        self._paths = {}
        cfg = configparser.ConfigParser()
        cfg.read(PATHS_CFG_FILE, encoding="utf-8")
        for key in cfg["paths"]:
            self._paths[key] = self._get_path(cfg["paths"][key].strip('"'))
        # Carga la fuente de datos.
        self.update_source()

    # Propiedades de la API
    @property
    def current_source(self) -> Path:
        """Devuelve la fuente de datos actual."""
        return self._source_db

    # Métodos de la API
    def update_source(self) -> None:
        """Actualiza la fuente utilizada a la más actual.

        Busca en el directorio indicado en la clave 'sources' del archivo de
        configuración principal.

        """
        self._source_db = get_most_recent_db(self._paths["sources-dir"], allow_prefixes=False)
        self._adapter = MarxAdapter(self._source_db)
        self._adapter.load()

    def save(self) -> None:
        """Guarda los cambios en la base de datos.

        La nueva base de datos generada llevará el nombre original con el
        sufijo "APIMOD_".

        """
        self._adapter.save(prefix="APIMOD")

    def autoquotas(self, date: datetime | None = None, cfg_file: Path | None = None) -> None:
        """Generador de cuotas mensuales.

        De no especificarse un archivo de configuración alternativo, se usará
        el cargado por defecto desde el archivo de configuración principal.

        """
        date = date or datetime.now()
        if not isinstance(date, datetime):
            raise ValueError(
                f"La fecha proporcionada debe tener formato 'datetime.datetime', no {type(date)!s}"
            )

        cfg_file = cfg_file or self._paths["autoquotas-config"]
        if not cfg_file.exists():
            raise FileNotFoundError(
                f"El archivo de configuración de cuotas mensuales proporcionado no existe."
            )
        source, amount, ratio, sinks = parse_nested_cfg(cfg_file)

        distr = Distribution(self._adapter.suite)
        distr.source = source
        if amount:
            distr.source.amount = amount
        if ratio:
            distr.source.ratio = ratio
        for sink in sinks:
            distr.sinks.new(**sink)
        distr.prepare(show=True)
        distr.run(date=date)

        print("******************************")
        print(distr.source)
        for sink in distr.sinks:
            print(sink)

    def set_path(self, key: str, new_path: str | Path) -> None:
        """Modifica el directorio o archivo usado por defecto para fuentes de
        datos o configuraciones.

        'key' debe ser una de las claves del archivo de rutas, es decir:
            - 'sources-dir'
            - 'wages-dir'
            - 'autoquotas-config'
            - 'autoinvest-config'
            - 'wageparser-config'

        Si no se encuentra la clave, se lanzará un error.

        """
        if key not in self._paths:
            raise KeyError(f"La clave '{key}' no se encuentra en el archivo de rutas.")
        self._paths[key] = self._get_path(Path(new_path))
        cfg = configparser.ConfigParser()
        cfg.read(PATHS_CFG_FILE, encoding="utf-8")
        cfg["paths"][key] = str(self._paths[key])
        with open(PATHS_CFG_FILE, "w", encoding="utf-8") as file:
            cfg.write(file)

    def copy_config(self, key: str, where: str | Path) -> Path:
        """Copia una configuración en un nuevo archivo para que pueda ser
        modificado por un usuario.

        Si 'where' es un directorio, el archivo se guardará con el mismo
        nombre; si es un archivo, se guardará con el nombre proporcionado,
        sobreescribiendo si ya existe.

        Devuelve la ruta del nuevo archivo.

        """
        if key not in self._paths:
            raise KeyError(f"La clave '{key}' no se encuentra en el archivo de rutas.")
        source = self._paths[key]
        dest = Path(where)
        if dest.is_dir():
            dest = dest / source.name
        shutil.copyfile(source, dest)
        return dest

    # Interno
    def _get_path(self, path: str | Path) -> Path:
        """Almacena una ruta a un archivo a partir de 'raw_path'.

        Si la ruta es relativa, la vuelve absoluta dentro de "marx".

        Si la ruta no existe, lanza un error.

        """
        path = Path(path)
        if not path.is_absolute():
            path = Path(str(Path(__file__).parent.parent) + "/config" + str(path))
        if not path.exists():
            raise FileNotFoundError(f"No se encuentra el archivo o directorio {path}")
        return path
