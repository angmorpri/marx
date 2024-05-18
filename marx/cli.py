# Python 3.10.11
# Creado: 11/05/2024
"""Cliente ligero para Marx por línea de comandos.

Actúa como una interfaz para la API de Marx, enmascarando todas las operaciones
como comandos.

Utiliza 'argparse' para gestionar los argumentos y opciones de la línea de
comandos.

"""

import argparse
from datetime import datetime

from marx import MarxAPI


class MarxCLI:
    """Cliente de línea de comandos para Marx.

    Implementa los comandos y opciones para operar Marx desde la terminal.
    Presenta dos modos de uso: directo e interactivo. En el modo directo, se
    ejecuta una única operación y se cierra el programa. En el modo
    interactivo, se abre un menú que permite realizar diferentes operaciones
    sin cerrar el programa.

    Recibe como único argumento la línea de comandos, a partir de la cuál
    se lanzará el modo interactivo (si no hay comandos) o el modo directo
    (si los hay).

    """

    def __init__(self, args: list[str]):
        self.marx = MarxAPI()
        if args:
            self.setup()
            args = self.parser.parse_args(args)
            args.func(args)
        else:
            self.setup(interactive=True)
            print(
                """
Bienvenido al gestor de finanzas personales

    ███    ███ █████ ██████ ██   ██ 
    ████  ██████   ████   ██ ██ ██  
    ██ ████ ███████████████   ███   
    ██  ██  ████   ████   ██ ██ ██  
    ██      ████   ████   ████   ██ 
            
Usa 'help' o 'h' para ver las opciones disponibles.

Usa 'exit' o 'x' para salir.            
"""
            )
            self._cont = True
            while self._cont:
                cmd = input("\n>>> ")
                try:
                    args = self.parser.parse_args(cmd.split())
                    args.func(args)
                except SystemExit:
                    continue

    def setup(self, interactive: bool = False):
        """Configura los comandos y opciones del CLI"""
        self.parser = argparse.ArgumentParser(description="Interfaz de línea de comandos para Marx")
        subparsers = self.parser.add_subparsers(required=True)

        # Comando "source"
        p_source = subparsers.add_parser(
            "source", aliases=["s"], help="Muestra o recarga la fuente de datos"
        )
        p_source.add_argument(
            "-u", "--update", action="store_true", help="Recarga la fuente de datos"
        )
        p_source.set_defaults(func=self._source)

        # Comando "save"
        p_save = subparsers.add_parser("save", help="Guarda los datos en un archivo")
        p_save.set_defaults(func=self._save)

        # Comando "autoquotas"
        p_autoquotas = subparsers.add_parser(
            "autoquotas", aliases=["autoq", "q"], help="Calcula la distribución de cuotas mensuales"
        )
        p_autoquotas.add_argument(
            "-d",
            "--date",
            action="store",
            help="Fecha de la distribución, en formato YYYY-MM-DD. Por defecto, hoy.",
        )
        p_autoquotas.add_argument(
            "--cfg",
            action="store",
            help="Archivo de configuración con los datos de la distribución",
        )
        p_autoquotas.set_defaults(func=self._autoquotas)

        # Comando "autoinvest"
        p_autoinvest = subparsers.add_parser(
            "autoinvest", aliases=["autoi", "i"], help="Calcula el reparto de inversiones"
        )
        p_autoinvest.add_argument(
            "-d",
            "--date",
            action="store",
            help="Fecha de la distribución, en formato YYYY-MM-DD. Por defecto, hoy.",
        )
        p_autoinvest.add_argument(
            "--cfg",
            action="store",
            help="Archivo de configuración con los datos de la distribución",
        )
        p_autoinvest.set_defaults(func=self._autoinvest)

        # Comando "wageparser"
        p_wageparser = subparsers.add_parser(
            "wageparser", aliases=["wage", "w"], help="Extrae los datos de un recibo de sueldo"
        )
        p_wageparser.add_argument(
            "-d",
            "--date",
            action="store",
            help="Fecha de la distribución, en formato YYYY-MM-DD. Por defecto, hoy.",
        )
        p_wageparser.add_argument(
            "-t",
            "--target",
            action="store",
            help="Nombre del archivo de recibo de sueldo a procesar, con extensión",
        )
        p_wageparser.add_argument(
            "--cfg",
            action="store",
            help="Archivo de configuración con los datos de la distribución",
        )
        p_wageparser.set_defaults(func=self._wageparser)

        # Comando "balance"
        p_balance = subparsers.add_parser(
            "balance", aliases=["b"], help="Genera un balance con los datos actuales"
        )
        p_balance.add_argument(
            "-s",
            "--start",
            action="store",
            help="Fecha de inicio del balance, en formato YYYY-MM-DD",
            required=True,
        )
        p_balance.add_argument(
            "-e",
            "--end",
            action="store",
            help="Fecha de fin del balance, en formato YYYY-MM-DD",
            required=True,
        )
        p_balance.add_argument(
            "-p",
            "--step",
            action="store",
            help="Intervalo de tiempo del balance, en formato 'Xd' o 'Xm' (días o meses). Por defecto, '1m.'",
        )
        p_balance.add_argument(
            "-o",
            "--output",
            action="store",
            help="Nombre del archivo de salida del balance. Por defecto, '{user-dir}/balance.xlsx'.",
        )
        p_balance.add_argument(
            "--sheet",
            action="store",
            help="Nombre o ID de la hoja de cálculo del archivo de salida. Por defecto, será la primera.",
        )
        p_balance.set_defaults(func=self._balance)

        # Comando "config"
        p_config = subparsers.add_parser(
            "config", aliases=["cfg"], help="Configura los parámetros del programa"
        )
        p_config.add_argument(
            "key",
            action="store",
            help="Nombre de la clave de configuración a modificar",
        )
        p_config.add_argument(
            "-s",
            "--set",
            action="store",
            nargs="?",
            const=True,
            help="Ruta del nuevo archivo para la clave",
        )
        p_config.add_argument(
            "-c",
            "--copy",
            action="store",
            nargs="?",
            const=True,
            help="Copiar archivo de configuración indicado por la clave",
        )
        p_config.set_defaults(func=self._config)

        # Comandos sólo disponibles en modo interactivo
        if interactive:
            p_exit = subparsers.add_parser("exit", aliases=["x"], help="Cerrar la interfaz")
            p_exit.set_defaults(func=self._exit)

            p_help = subparsers.add_parser("help", aliases=["h"], help="Muestra esta ayuda")
            p_help.set_defaults(func=lambda _: self.parser.print_help())

    # Comandos

    def _source(self, args: argparse.Namespace) -> None:
        """Muestra o recarga la fuente de datos"""
        if args.update:
            self.marx.update_source()
        print(f"Fuente de datos actual: {self.marx.current_source}")

    def _exit(self, args: argparse.Namespace) -> None:
        """Cerrar la interfaz"""
        print("¡Hasta luego!\n\n")
        self._cont = False

    def _save(self, args: argparse.Namespace) -> None:
        """Guarda los datos en un archivo"""
        self.marx.save()
        print("Datos guardados correctamente.")

    def _autoquotas(self, args: argparse.Namespace) -> None:
        """Calcula la distribución de cuotas mensuales"""
        date = datetime.strptime(args.date, "%Y-%m-%d") if args.date else datetime.now()
        res = self.marx.autoquotas(date, args.cfg)
        res.show()
        print("\nEventos generados:")
        for event in res.events:
            print("    ", event)

    def _autoinvest(self, args: argparse.Namespace) -> None:
        """Calcula el reparto de inversiones"""
        date = datetime.strptime(args.date, "%Y-%m-%d") if args.date else datetime.now()
        res = self.marx.autoinvest(date, args.cfg)
        res.show()
        print("\nEventos generados:")
        for event in res.events:
            print("    ", event)

    def _wageparser(self, args: argparse.Namespace) -> None:
        """Extrae los datos de un recibo de sueldo"""
        date = datetime.strptime(args.date, "%Y-%m-%d") if args.date else datetime.now()
        path, events = self.marx.wageparser(args.target, date, args.cfg)
        print(f"Datos extraídos correctamente de {path}.")
        print("Eventos generados:")
        for event in events:
            print(" - ", event)

    def _balance(self, args: argparse.Namespace) -> None:
        """Genera un balance con los datos actuales"""
        if args.sheet:
            if args.sheet.isdigit():
                args.sheet = int(args.sheet)
        res = self.marx.balance(
            datetime.strptime(args.start, "%Y-%m-%d"),
            datetime.strptime(args.end, "%Y-%m-%d"),
            args.step,
            args.output,
            args.sheet or 0,
        )
        print(f"Balance guardado en '{res}'.")

    def _config(self, args: argparse.Namespace) -> None:
        """Configura los parámetros del programa"""
        if args.key not in self.marx.paths.keys():
            print(f"Clave de configuración '{args.key}' no válida.")
            return
        if not args.set and not args.copy:
            print(self.marx.paths.request(args.key))
        elif args.copy:
            if args.copy is True:
                dest = self.marx.copy_config(args.key)
            else:
                dest = self.marx.copy_config(args.key, args.copy)
            print(f"Archivo de configuración para {args.key} copiado a '{dest}'.")
            if args.set is True:
                self.marx.set_path(args.key, dest)
                print(f"Ruta para {args.key} cambiada a '{dest}'.")
        elif args.set:
            if args.set is True:
                print("Ruta de archivo no especificada.")
                return
            res = self.marx.set_path(args.key, args.set)
            print(f"Ruta para {args.key} cambiada a '{res}'.")
