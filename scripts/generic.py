# Python 3.10.11
# Creado: 24/01/2024
"""Para hacer pequeñas pruebas de código."""
import os
import sys

MARX_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__) + "/marx"))
sys.path.append(os.path.dirname(MARX_DIR))


from cli import MarxCLI


if __name__ == "__main__":
    MarxCLI(sys.argv[1:])
