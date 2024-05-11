# Python 3.10.11
# Creado: 25/03/2024
"""API de Marx.

Define la clase "MarxAPI", que se puede instanciar para interactuar con todas
las herramientas del programa.

"""

import shutil

from datetime import datetime
from pathlib import Path

from dateutil.relativedelta import relativedelta

from marx.automation import Distribution, WageParser
from marx.model import MarxAdapter, Event
from marx.reporting import Balance
from marx.util import get_most_recent_db, Pathfinder


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

    El constructor no recibe argumentos.

    """

    def __init__(self) -> None:
        self.paths = Pathfinder(PATHS_CFG_FILE)
        self.update_source()

    # Propiedades de la API
    @property
    def current_source(self) -> Path:
        """Devuelve la fuente de datos actual."""
        return self._source_db

    # Métodos de la API
    def update_source(self) -> None:
        """Actualiza la fuente utilizada a la más actual.

        Utiliza la clave "sources-dir" del archivo de rutas.

        """
        sources_dir = self.paths.request("sources-dir")
        self._source_db = get_most_recent_db(sources_dir, allow_prefixes=False)
        self._adapter = MarxAdapter(self._source_db)
        self._adapter.load()

    def save(self) -> None:
        """Guarda los cambios en la base de datos.

        La nueva base de datos generada llevará el nombre original con el
        sufijo "APIMOD_".

        """
        self._adapter.save(prefix="APIMOD")

    def autoquotas(
        self, date: datetime | None = None, cfg_file: Path | None = None
    ) -> Distribution:
        """Generador de cuotas mensuales.

        De no especificarse un archivo de configuración alternativo, se usará
        el cargado por defecto desde el archivo de configuración principal.

        Devuelve la distribución generada.

        """
        date = date or datetime.now()
        if not isinstance(date, datetime):
            raise ValueError(
                f"La fecha proporcionada debe tener formato 'datetime.datetime', no {type(date)!s}"
            )

        if cfg_file:
            cfg_file = self.paths.resolve(cfg_file)
        else:
            cfg_file = self.paths.request("autoquotas-config")
        if not cfg_file.exists():
            raise FileNotFoundError(
                f"El archivo de configuración de cuotas mensuales proporcionado no existe."
            )

        distr = Distribution.from_cfg(self._adapter.suite, cfg_file)
        distr.prepare(verbose=False)
        distr.run(date=date)

        return distr

    def autoinvest(
        self, date: datetime | None = None, cfg_file: Path | None = None
    ) -> Distribution:
        """Generador de inversiones mensuales.

        De no especificarse un archivo de configuración alternativo, se usará
        el cargado por defecto desde el archivo de configuración principal.

        Devuelve la distribución generada.

        """
        date = date or datetime.now()
        if not isinstance(date, datetime):
            raise ValueError(
                f"La fecha proporcionada debe tener formato 'datetime.datetime', no {type(date)!s}"
            )

        if cfg_file:
            cfg_file = self.paths.resolve(cfg_file)
        else:
            cfg_file = self.paths.request("autoinvest-config")
        if not cfg_file.exists():
            raise FileNotFoundError(
                f"El archivo de configuración de inversiones mensuales proporcionado no existe."
            )

        distr = Distribution.from_cfg(self._adapter.suite, cfg_file)
        distr.prepare(verbose=False)
        distr.run(date=date)
        return distr

    def wageparser(
        self, target: str | None = None, date: datetime | None = None, cfg_file: Path | None = None
    ) -> tuple[Path, list[Event]]:
        """Generador de eventos derivados de la nómina.

        'target' debe ser el nombre del archivo de nómina a procesar (sin
        extensión), que se buscará en el directorio indicado en la clave
        'wages-dir' del archivo de configuración principal, y en todos los
        subdirectorios. Si no se especifica ninguno, se escogerá el más
        reciente, de acuerdo a su fecha de creación.

        De no especificarse un archivo de configuración alternativo, se usará
        el cargado por defecto desde el archivo de configuración principal.

        Devuelve la ruta de la nómina parseada, y la lista de eventos
        generados.

        """
        wages_dir = self.paths.request("wages-dir")
        if target is None:
            wage_file = sorted(wages_dir.glob("*.pdf"), key=lambda x: x.stat().st_ctime)[-1]
        else:
            for file in wages_dir.glob("**/*.pdf"):
                if target in file.name:
                    wage_file = file
                    break
            else:
                raise FileNotFoundError(
                    f"No se encuentra el archivo de nómina con nombre {target}"
                    f" en {wages_dir!s} o sus subdirectorios"
                )

        date = date or datetime.now()
        if not isinstance(date, datetime):
            raise ValueError(
                f"La fecha proporcionada debe tener formato 'datetime.datetime', no {type(date)!s}"
            )

        if cfg_file:
            cfg_file = self.paths.resolve(cfg_file)
        else:
            cfg_file = self.paths.request("wageparser-config")
        if not cfg_file.exists():
            raise FileNotFoundError(
                f"El archivo de configuración del parser de nóminas proporcionado no existe."
            )

        wp = WageParser(self._adapter.suite, cfg_path=cfg_file)
        events = wp.parse(wage_file, date=date, verbose=False)
        return wage_file, events

    def balance(
        self,
        start: datetime,
        end: datetime,
        step: str = "1m",
        output: Path | None = None,
        sheet_id: int | str = 0,
    ) -> Path:
        """Genera un balance para ciertas fechas.

        'start' y 'end' deben ser fechas en formato 'datetime.datetime'.

        'step' debe ser una cadena compuesta por un número y una de las
        siguientes letras para indicar el paso de tiempo:
            - 'd' para días
            - 'w' para semanas
            - 'm' para meses
            - 'y' para años
        Por ejemplo, "1d" generará un balance diario, "2w" uno cada dos
        semanas, etc.

        'end' sólo se incluirá en el balance si coincide exactamente con un
        paso de tiempo.

        Si se quiere especificar una ruta o un archivo donde volcar el
        resultado, se debe usar el parámetro 'output'. Si no se especifica,
        se almacenará en el directorio indicado por la clave 'user-dir' en la
        configuración principal. Si se indica un directorio pero no un nombre,
        el nombre por defecto será "balance.xlsx", sobrescribiendo si ya
        existe.

        Por otro lado, si se indica un archivo existente, se puede indicar un
        índice de hoja donde volcar los datos, sobrescribiendo lo que hubiera
        previamente. Este índice puede ser o bien un entero indicando la
        posición de la hoja, o bien una cadena con el nombre de la hoja. Si no
        se indica, se sobrescribirá el documento al completo. Si no se indicó
        un archivo, se ignorará este parámetro.

        Devuelve la ruta del archivo Excel generado.

        """
        # Tiempos
        if not isinstance(start, datetime) or not isinstance(end, datetime):
            raise ValueError("Las fechas de inicio y fin deben ser de tipo 'datetime.datetime'.")
        if start > end:
            raise ValueError("La fecha de inicio no puede ser posterior a la de fin.")
        if not isinstance(step, str):
            raise ValueError("El paso de tiempo debe ser una cadena.")
        step, unit = int(step[:-1]), step[-1]
        if unit not in ("d", "w", "m", "y"):
            raise ValueError("El paso de tiempo debe indicarse mediante 'd', 'w', 'm' o 'y'.")
        unit = {"d": "days", "w": "weeks", "m": "months", "y": "years"}[unit]
        dates = [start]
        while dates[-1] < end:
            dates.append(dates[-1] + relativedelta(**{unit: +step}))

        # Archivo de salida
        output = output or self.paths.request("user-dir")
        if not output.exists():
            raise FileNotFoundError(f"El archivo o directorio de salida no existe.")
        if output.is_dir():
            output /= "balance.xlsx"

        # Resultado
        balance = Balance(self._adapter.suite)
        table = balance.build(*dates)
        output = balance.report(table, format="excel", output=output, sheet=sheet_id)
        return output

    def set_path(self, key: str, new_path: str | Path) -> None:
        """Modifica el directorio o archivo usado por defecto para fuentes de
        datos o configuraciones.

        'key' debe ser una de las claves del archivo de rutas, es decir:
            - 'sources-dir'
            - 'wages-dir'
            - 'user-dir'
            - 'autoquotas-config'
            - 'autoinvest-config'
            - 'wageparser-config'

        Si no se encuentra la clave, se lanzará un error.

        """
        self.paths.change(key, new_path)

    def copy_config(self, key: str, where: str | Path | None = None) -> Path:
        """Copia una configuración en un nuevo archivo para que pueda ser
        modificado por un usuario.

        Si 'where' es un directorio, el archivo se guardará con el mismo
        nombre; si es un archivo, se guardará con el nombre proporcionado,
        sobrescribiendo si ya existe. Si no se especifica, se guardará en el
        directorio indicado por la clave 'user-dir'.

        Devuelve la ruta del nuevo archivo.

        """
        if key not in self.paths.keys():
            raise KeyError(f"La clave '{key}' no se encuentra en el archivo de rutas.")
        source = self.paths.request(key)
        if where is None:
            where = self.paths.request("user-dir")
        dest = Path(where)
        if dest.is_dir():
            dest = dest / source.name
        if dest.exists():
            dest.unlink()
        shutil.copyfile(source, dest)
        return dest
