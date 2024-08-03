# Python 3.10.11
# Creado: 03/08/2024
"""Test del cliente"""
import os
import sys

MARX_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__) + "/marx"))
sys.path.append(os.path.dirname(MARX_DIR))


from pathlib import Path

from marx.cli import MarxCLI


USERCONFIG = Path(__file__).parent / "files" / "marxuserconfig.toml"


if __name__ == "__main__":
    marxcli = MarxCLI(USERCONFIG)

    print(">>> load")
    marxcli.load()

    print(">>> load auto")
    marxcli.load("auto")

    print(">>> load pick")
    marxcli.load("pick")

    print(">>> load MOD_Ago_03_2024_ExpensoDB")
    marxcli.load("MOD_Ago_03_2024_ExpensoDB")

    print(">>> load C:/Users/angel/Programación/projects/marx/tests/data/Jul_04_2024_ExpensoDB")
    marxcli.load("C:/Users/angel/Programación/projects/marx/tests/data/Jul_04_2024_ExpensoDB")
