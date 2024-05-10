# Python 3.10.11
# Creado: 11/05/2024
"""CLI para Marx.

Permite ejecutar Marx desde la línea de comandos, con diferentes opciones y
argumentos. También implementa un menú interactivo para facilitar el uso del
programa.

Se basa en el uso de "argparse" para gestionar los argumentos y opciones de la
línea de comandos.

"""

import argparse

from marx import MarxAPI


class MarxCLI:
    """CLI para Marx.

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
            print("¡Bienvenido a Marx! Usa 'exit' para salir.")
            while True:
                try:
                    args = self.parser.parse_args(input("> ").split())
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

        if interactive:
            p_exit = subparsers.add_parser("exit", help="Cerrar la interfaz")
            p_exit.set_defaults(func=self._exit)

    # Comandos

    def _source(self, args: argparse.Namespace) -> None:
        """Muestra o recarga la fuente de datos"""
        if args.update:
            self.marx.update_source()
        print(self.marx.current_source)

    def _exit(self, args: argparse.Namespace) -> None:
        """Cerrar la interfaz"""
        print("¡Hasta luego!")
        exit(0)
