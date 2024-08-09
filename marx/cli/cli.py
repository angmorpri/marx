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
import os
from pathlib import Path
from typing import Literal

from more_itertools import always_iterable

from marx.cli.wrapper import MarxAPIWrapper
from marx.cli.userconfig import UserConfig


def error(message: str) -> None:
    """Imprime un mensaje de error"""
    print(f"[ERROR] {message}")


class MarxCLI:
    """Cliente básico para Marx por línea de comandos

    Tiene dos modos de uso: intérprete de argumentos ('parse'), o menú
    interactivo ('menu').

    Requiere de un archivo de configuración de usuario en formato TOML. Si no
    se proporciona uno, tratará de cargarlo de la variable de entorno
    'MARX_USERCONFIG'. Si no se encuentra o hay un error al cargarlo, lanzará
    una excepción.

    """

    def __init__(self, userconfig_path: str | Path | None = None) -> None:
        # Archivo de configuración de usuario
        if not userconfig_path:
            userconfig_path = os.getenv("MARX_USERCONFIG")
            if not userconfig_path:
                raise ValueError("No se ha proporcionado un archivo de configuración de usuario")
        self.userconfig_path = Path(userconfig_path)

        # Inicialización
        self.userconfig = UserConfig(self.userconfig_path)
        self.marx = MarxAPIWrapper(self.userconfig)

    # Modos de ejecución

    def parse(self, args: list[str]) -> None:
        """Procesa los argumentos de la línea de comandos"""
        self.setup()
        self.autorun("on_cli_startup", fallback=["load auto"])
        args = self.parser.parse_args(args)
        try:
            args.func(args)
        except (KeyError, ValueError, FileNotFoundError) as e:
            error(str(e))
        self.autorun("on_cli_shutdown", fallback=["save auto"])

    def menu(self) -> None:
        """Inicia un intérprete interactivo"""
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

Puede comenzar cargando una base de datos con 'load'.

"""
        )
        self.autorun("on_cli_startup")
        self._cont = True
        while self._cont:
            # esperar comando
            try:
                command = input(">>> ")
            except KeyboardInterrupt:
                command = "exit"
            if not command:
                continue
            # ejecutar comando
            try:
                args = self.parser.parse_args(command.split())
                args.func(args)
            except (KeyError, ValueError, FileNotFoundError) as e:
                error(str(e))
            except SystemExit:
                print()
                pass
        self.autorun("on_cli_shutdown")

    # Comandos de menú

    def config(self, key: Literal["show", "reload"]) -> None:
        """Muestra o recarga la configuración de usuario"""
        if key == "show":
            print(self.userconfig.path)
        elif key == "reload":
            self.userconfig = UserConfig(self.userconfig_path)
            self.marx.userconfig = self.userconfig
            print("Configuración recargada")

    def exit(self) -> None:
        """Sale del intérprete interactivo"""
        print("¡Hasta luego!\n\n")
        self._cont = False

    # Métodos internos

    def autorun(self, key: str, fallback: list[str] | None = None) -> None:
        """Ejecuta comandos automáticamente"""
        user_command = self.userconfig.get(key, safe=False)
        commands = user_command or fallback or []
        for command in always_iterable(commands):
            print(f">>> {command}")
            args = self.parser.parse_args(command.split())
            try:
                args.func(args)
            except (KeyError, ValueError, FileNotFoundError) as e:
                error(str(e))

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
        load_parser.set_defaults(func=lambda args: self.marx.load(args.key))

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
        save_parser.set_defaults(func=lambda args: self.marx.save(args.key))

        # Comando 'autoquotas'
        autoq_parser = subparsers.add_parser(
            "autoquotas", aliases=["autoq"], help="Distribuir automáticamente las cuotas mensuales"
        )
        autoq_parser.add_argument(
            "-d", "--date", default=None, help="Fecha de imputación de las cuotas"
        )
        autoq_parser.set_defaults(func=lambda args: self.marx.autoquotas(args.date))

        # Comando 'autoinvest'
        autoi_parser = subparsers.add_parser(
            "autoinvest", aliases=["autoi"], help="Distribuir automáticamente inversiones"
        )
        autoi_parser.add_argument(
            "-d", "--date", default=None, help="Fecha de imputación de las inversiones"
        )
        autoi_parser.set_defaults(func=lambda args: self.marx.autoinvest(args.date))

        # Comando 'distr'
        distr_parser = subparsers.add_parser(
            "distr", help="Distribuir automáticamente según el archivo de criterios indicado"
        )
        distr_parser.add_argument("criteria_path", help="Ruta del archivo de criterios")
        distr_parser.add_argument(
            "-d", "--date", default=None, help="Fecha de imputación de las cuotas"
        )
        distr_parser.set_defaults(func=lambda args: self.marx.distr(args.criteria_path, args.date))

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
            func=lambda args: self.marx.paycheck(args.paycheck_path, args.criteria_path, args.date)
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
        loans_list_parser.set_defaults(func=lambda args: self.marx.loans_list(args.date))

        loans_default_parser = loans_subparsers.add_parser(
            "default", help="Marcar un préstamo como default"
        )
        loans_default_parser.add_argument("tag", help="Etiqueta del préstamo")
        loans_default_parser.set_defaults(func=lambda args: self.marx.loans_default(args.tag))

        # Comandos para modo interactivo
        if interactive:
            source_parser = subparsers.add_parser(
                "source", aliases=["current"], help="Mostrar la base de datos actualmente cargada"
            )
            source_parser.set_defaults(func=lambda _: self.marx.source())

            config_parser = subparsers.add_parser(
                "config", aliases=["cfg"], help="Configuración de usuario"
            )
            config_parser.set_defaults(func=lambda _: self.config("show"))
            config_subparsers = config_parser.add_subparsers()
            reload_config_parser = config_subparsers.add_parser(
                "reload", aliases=["r"], help="Recargar la configuración de usuario"
            )
            reload_config_parser.set_defaults(func=lambda _: self.config("reload"))

            exit_parser = subparsers.add_parser(
                "exit", aliases=["x"], help="Salir del intérprete interactivo"
            )
            exit_parser.set_defaults(func=lambda _: self.exit())

            help_parser = subparsers.add_parser("help", aliases=["h"], help="Mostrar ayuda")
            help_parser.set_defaults(func=lambda _: self.parser.print_help())
