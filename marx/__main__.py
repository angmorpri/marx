# Python 3.10.11
# Creado: 09/08/2024

import sys

from marx.cli import MarxCLI


def main():
    if len(sys.argv) > 1:
        MarxCLI().parse(sys.argv[1:])
    else:
        MarxCLI().menu()
        input("Pulse cualquier tecla para salir...")


if __name__ == "__main__":
    main()
