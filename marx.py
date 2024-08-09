# Python 3.10.11
# Creado: 09/08/2024

import sys
from pathlib import Path

from marx.cli import MarxCLI


if __name__ == "__main__":
    if len(sys.argv) > 1:
        marxcli = MarxCLI().parse(sys.argv[1:])
    else:
        marxcli = MarxCLI().menu()
        input("Pulse cualquier tecla para salir...")
