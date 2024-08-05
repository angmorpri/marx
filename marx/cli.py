# Python 3.10.11
# Creado: 28/06/2024
"""Cliente por defecto para Marx

Presenta la clase 'MarxCLI', que se puede instanciar para interactuar con la
API de Marx desde la línea de comandos. Tiene dos modos de ejecución: si se le
pasan argumentos, los ejecutará sobre la API directamente y devolverá el
resultado; si no, se abrirá un intérprete interactivo.

"""

# TODO: config reload, exit, current

import argparse
import re
from datetime import datetime
from pathlib import Path
from tkinter import filedialog as fd
from typing import Any

import toml
from more_itertools import always_iterable

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

CLI_ERROR = object()


def error(message: str) -> None:
    """Imprime un mensaje de error"""
    print(f"[ERROR] {message}")


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
        self.config = toml.load(path)

    def get(self, key: str, *, safe: bool = True) -> Any:
        """Devuelve el valor de la clave 'key', en cualquier sección del
        archivo de configuración

        Si la clave no se encuentra, o se encuentra pero está vacía, se
        imprimirá el mensaje de error pertinentes y se devolverá el código de
        error. Esto se puede evitar indicando 'safe=False', en cuyo caso, no
        se mostrará ningún mensaje y se devolverá 'None'.

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
        else:
            if safe:
                error(f"No se ha encontrado la clave '{key}' en el archivo de configuración")
                return CLI_ERROR
            return None
        # está vacía
        if not res:
            if safe:
                error(f"El parámetro con clave '{key}' está vacío")
                return CLI_ERROR
            return None
        # cast
        if key.endswith("_dir") or key.endswith("_path"):
            return Path(res)
        return res


class MarxCLI:
    """Cliente simple para Marx

    El cliente puede lanzarse de tres modos:
    1. Usar el objeto generado tras instanciar la clase para ejecutar
    directamente los métodos wrapper de la API de Marx. Recomendado para
    testing.
    2. Llamar al método 'args' con una lista de argumentos de línea de
    comandos, normalmente obtenidos de 'sys.argv'. Ejecutará el comando
    indicado.
    3. Llamar al método 'interactive' para abrir un intérprete interactivo.

    Tanto en el caso (2) como (3), al inicializarse tratará de lanzar el o los
    comandos especificados en el archivo de configuración de usuario como
    'on_cli_startup', y, al cerrarse, los que se especifiquen en
    'on_cli_shutdown'. En el caso del modo argumentos, si no se indican,
    lanzará por defecto 'load auto' y 'save auto', respectivamente. En caso
    del modo interactivo, no se lanzará ningún comando por defecto.

    El constructor, en cualquier modo, debe recibir la ruta del archivo de
    configuración de usuario.

    """

    def __init__(self, userconfig_path: str | Path) -> None:
        self.marx = Marx()
        self.userconfig = UserConfig(Path(userconfig_path))

    def args(self, args: list[str]) -> None:
        """Procesa los argumentos de la línea de comandos"""
        self.setup()
        self.autorun("on_cli_startup", allback=["load auto"])
        args = self.parser.parse_args(args)
        args.func(args)
        self.autorun("on_cli_shutdown", fallback=["save auto"])

    def interactive(self) -> None:
        """Inicia un intérprete interactivo"""
        self.setup(interactive=True)
        self.autorun("on_cli_startup")
        while True:
            try:
                command = input(">>> ")
                if not command:
                    continue
                args = self.parser.parse_args(command.split())
                args.func(args)
            except KeyboardInterrupt:
                self.parser.parse_args(["exit"])
            except SystemExit:
                continue
        self.autorun("on_cli_shutdown")

    # Métodos de ayuda interna

    def validate_path(self, path: str | Path) -> Path:
        """Verifica que 'path' es una ruta válida

        Si no lo es, muestra un mensaje de error y devuelve el código de error.
        Si 'path' está vacío, lanzará una excepción.

        Convierte 'path' a un objeto 'Path' si no lo es ya.

        """
        if not path:
            raise ValueError("Se ha pasado una ruta vacía a 'validate_path'")
        path = Path(path)
        if not path.exists():
            error(f"La ruta '{path}' no existe")
            return CLI_ERROR
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
        if choice is None:
            error(f"No se ha encontrado ninguna base de datos en '{path}'")
            return CLI_ERROR
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
        if choice is None:
            error(f"No se ha encontrado ninguna nómina en '{path}'")
            return CLI_ERROR
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
            error(f"Formato de fecha no válida: {date!r}")
            return CLI_ERROR
        if len(blocks[0]) == 4:
            return datetime.strptime("-".join(blocks), "%Y-%m-%d")
        elif len(blocks[2]) == 4:
            return datetime.strptime("-".join(blocks), "%d-%m-%Y")
        print(f"Formato de fecha no reconocido: {date!r}")
        return CLI_ERROR

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
            if path is CLI_ERROR:
                return
        else:
            path = Path(key)
            if not path.is_absolute():
                path = self.userconfig.get("databases_dir")
                if path is CLI_ERROR:
                    return
                path /= key
        # Verificar que la ruta es válida
        path = self.validate_path(path)
        if path is CLI_ERROR:
            return
        # Cargar la base de datos
        if key == "auto":
            path = self.most_recent_db(path)
        elif key == "pick":
            path = self.dialog_load(path)
        if not path.is_file():
            error(f"La ruta proporcionada '{path}' no es un archivo de base de datos")
            return
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
        if criteria is CLI_ERROR:
            return
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
        if criteria is CLI_ERROR:
            return
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
        if date is CLI_ERROR:
            return
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
        if date is CLI_ERROR:
            return
        # criteria
        if not criteria_path:
            criteria_path = self.userconfig.get("paycheckparser_criteria_path")
            if criteria_path is CLI_ERROR:
                return
            criteria_path = self.validate_path(criteria_path)
        # paycheck
        if not paycheck_path:
            paychecks_dir = self.userconfig.get("paychecks_dir")
            if paychecks_dir is CLI_ERROR:
                return
            paycheck_path = self.most_recent_paycheck(paychecks_dir)
            print(f"Se ha seleccionado la nómina más reciente: '{paycheck_path}'")
        else:
            paycheck_path = Path(paycheck_path)
            if not paycheck_path.is_absolute():
                paychecks_dir = self.userconfig.get("paychecks_dir")
                if paychecks_dir is CLI_ERROR:
                    return
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
        date = self.parse_date(date)
        if date is CLI_ERROR:
            return
        res = self.marx.loans_list(date)
        print(f"Préstamos y deudas hasta fecha del {date:%Y-%m-%d}:")
        for tag, info in res.items():
            sign = "-" if info["position"] == 1 else "+"
            status = (
                "Abierta"
                if info["status"] == 0
                else "Cerrada" if info["status"] == 1 else "Default"
            )
            span = (
                f"{info['start_date']} - {info['end_date']}"
                if info["end_date"]
                else f"{info['start_date']} - "
            )
            print(
                f"> {tag: <12} ({status}, {span: <23})  {sign}{info['amount']:8.2f} € ({info['paid']:8.2f} € / {info['remaining']:8.2f} €)"
            )
        print()

    def loans_default(self, tag: str) -> None:
        """Marca un préstamo o deuda identificado con la etiqueta 'tag' como
        default

        """
        loans = self.marx.loans_list(datetime.now())
        if tag not in loans:
            error(f"No se ha encontrado el préstamo con etiqueta '{tag}'")
            return
        self.marx.loans_default(tag)
        print(f"Préstamo {tag!r} marcado exitosamente como default")

    # Métodos de la interfaz de usuario

    def setup(self, *, interactive: bool = False) -> None:
        """Configura los comandos y opciones de la interfaz de usuario"""
        self.parser = argparse.ArgumentParser(description="Interfaz de usuario para Marx")
        subparsers = self.parser.add_subparsers(required=True)

        # Comando 'load'
        load_parser = subparsers.add_parser(
            "load", aliases=["l"], help="Cargar una base de datos de Marx"
        )
        load_parser.add_argument(
            "key", nargs="?", default=None, help="Modo de carga o ruta de la base de datos a cargar"
        )
        load_parser.set_defaults(func=lambda args: self.load(args.key))

        # Comando 'save'
        save_parser = subparsers.add_parser(
            "save", aliases=["s"], help="Guardar la base de datos actual de Marx"
        )
        save_parser.add_argument(
            "key",
            nargs="?",
            default=None,
            help="Modo de guardado o ruta de la base de datos a guardar",
        )
        save_parser.set_defaults(func=lambda args: self.save(args.key))

        # Comando 'autoquotas'
        autoq_parser = subparsers.add_parser(
            "autoquotas", aliases=["autoq"], help="Distribuir automáticamente las cuotas mensuales"
        )
        autoq_parser.add_argument(
            "-d", "--date", default=None, help="Fecha de imputación de las cuotas"
        )
        autoq_parser.set_defaults(func=lambda args: self.autoquotas(args.date))

        # Comando 'autoinvest'
        autoi_parser = subparsers.add_parser(
            "autoinvest", aliases=["autoi"], help="Distribuir automáticamente inversiones"
        )
        autoi_parser.add_argument(
            "-d", "--date", default=None, help="Fecha de imputación de las inversiones"
        )
        autoi_parser.set_defaults(func=lambda args: self.autoinvest(args.date))

        # Comando 'distr'
        distr_parser = subparsers.add_parser(
            "distr", help="Distribuir automáticamente según el archivo de criterios indicado"
        )
        distr_parser.add_argument("criteria_path", help="Ruta del archivo de criterios")
        distr_parser.add_argument(
            "-d", "--date", default=None, help="Fecha de imputación de las cuotas"
        )
        distr_parser.set_defaults(func=lambda args: self.distr(args.criteria_path, args.date))

        # Comando 'paycheck'
        paycheck_parser = subparsers.add_parser(
            "paycheck", aliases=["pc"], help="Interpretar archivos de nóminas"
        )
        paycheck_parser.add_argument(
            "-p", "--paycheck-path", default=None, help="Ruta del archivo de nómina"
        )
        paycheck_parser.add_argument(
            "-c", "--criteria-path", default=None, help="Ruta del archivo de criterios"
        )
        paycheck_parser.add_argument(
            "-d", "--date", default=None, help="Fecha de imputación de las cuotas"
        )
        paycheck_parser.set_defaults(
            func=lambda args: self.paycheck(args.paycheck_path, args.criteria_path, args.date)
        )

        # Comando 'loans'
        loans_parser = subparsers.add_parser("loans", help="Gestionar préstamos y deudas")
        loans_subparsers = loans_parser.add_subparsers()

        loans_list_parser = loans_subparsers.add_parser(
            "list", aliases=["ls"], help="Listar préstamos y deudas"
        )
        loans_list_parser.add_argument(
            "-d", "--date", default=None, help="Fecha de corte para la lista"
        )
        loans_list_parser.set_defaults(func=lambda args: self.loans_list(args.date))

        loans_default_parser = loans_subparsers.add_parser(
            "default", help="Marcar un préstamo como default"
        )
        loans_default_parser.add_argument("tag", help="Etiqueta del préstamo")
        loans_default_parser.set_defaults(func=lambda args: self.loans_default(args.tag))

    def autorun(self, key: str, fallback: list[str] | None = None) -> None:
        """Ejecuta comandos automáticamente"""
        fallback = fallback or []
        user_command = self.userconfig.get(key, safe=True)
        if user_command is None:
            for command in fallback:
                args = self.parser.parse_args(command.split())
                args.func(args)
        else:
            for command in always_iterable(user_command):
                args = self.parser.parse_args(command.split())
                args.func(args)
