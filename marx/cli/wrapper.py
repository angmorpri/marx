# Python 3.10.11
# Creado: 09/08/2024
"""Wrapper para los métodos de la API de Marx"""

from datetime import datetime
from pathlib import Path

from marx.api import Marx
from marx.cli.userconfig import UserConfig
from marx.cli.util import (
    dialog,
    most_recent_db,
    most_recent_paycheck,
    parse_date,
    validate_path,
)
from marx.util import safely_rename_file


class MarxAPIWrapper:
    """Adapta la API de Marx para su uso en la interfaz de usuario

    Sobre todo presenta mecanismos auxiliares para cargar archivos e indicar
    parámetros de forma más sencilla, orientado a la línea de comandos.

    El constructor recibe únicamente un controlador de la configuración de
    usuario.

    """

    def __init__(self, userconfig: UserConfig) -> None:
        self.marx = Marx()
        self.userconfig = userconfig

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
        path = validate_path(path)
        # Cargar la base de datos
        if key == "auto":
            path = most_recent_db(path)
            print("Se selecciona la base de datos más reciente de forma automática")
        elif key == "pick":
            path = dialog.load(path)
        if not path.is_file():
            raise FileNotFoundError(
                f"La ruta proporcionada '{path}' no es un archivo de base de datos"
            )
        self.marx.load(path)
        print(f"Se ha cargado la base de datos del archivo '{path}'")

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
            new_path = dialog.save(default_path.parent)
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
        new_path = validate_path(new_path)
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

    def distr(
        self, criteria_path: str | Path, date: str | datetime | None = None
    ) -> None:
        """Distribuye automáticamente según el archivo de criterios indicado
        en 'criteria_path'

        'date' es la fecha en la que se imputarán las cuotas; si es None, usará
        la fecha actual; si es una cadena de caracteres, tendrá que tener
        formato 'YYYYMMDD', 'YYYY-MM-DD' o 'DD-MM-YYYY', teniendo en cuenta que '-' puede
        ser cualquier caracter no alfanumérico, o incluso ninguno.

        """
        date = parse_date(date)
        criteria_path = validate_path(criteria_path)
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
        date = parse_date(date)
        # criteria
        if not criteria_path:
            criteria_path = self.userconfig.get("paycheckparser_criteria_path")
            criteria_path = validate_path(criteria_path)
        # paycheck
        if not paycheck_path:
            paychecks_dir = self.userconfig.get("paychecks_dir")
            paycheck_path = most_recent_paycheck(paychecks_dir)
            print(f"Se ha seleccionado la nómina más reciente: '{paycheck_path}'")
        else:
            paycheck_path = Path(paycheck_path)
            if not paycheck_path.is_absolute():
                paychecks_dir = self.userconfig.get("paychecks_dir")
                paycheck_path = paychecks_dir / paycheck_path
        paycheck_path = validate_path(paycheck_path)
        # distribución
        res = self.marx.paycheck_parse(paycheck_path, criteria_path, date)
        print("Distribución realizada con éxito")
        events_date = res["events"][-1]["date"]
        print(f"Eventos generados para fecha {events_date}:")
        for event in res["events"]:
            sign = "+" if event["flow"] == 1 else "-" if event["flow"] == -1 else "="
            catcode = event["category"]["code"]
            orig2dest = (
                f"({event['orig']['repr_name']: <12} -> {event['dest']['repr_name']})"
            )
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
        date = parse_date(date)
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
            raise KeyError(
                f"No se ha encontrado ningún préstamo con la etiqueta {tag!r}"
            )
        self.marx.loans_default(tag)
        print(f"Préstamo {tag!r} marcado exitosamente como default")

    # Comandos extra

    def source(self) -> None:
        """Muestra la base de datos actualmente cargada"""
        if self.marx.mapper is None:
            print(
                "No hay ninguna base de datos cargada todavía. Usa el comando 'load' para cargar una."
            )
        else:
            print(self.marx.mapper.source)
