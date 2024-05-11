# Python 3.10.11
# Creado: 11/05/2024
"""Lanza la interfaz de línea de comandos de Marx.

Script para ser ejecutado como módulo principal de la aplicación.

"""

from marx.cli import MarxCLI

if __name__ == "__main__":
    try:
        MarxCLI([])
    except Exception as e:
        print(f"Error: {e}")
        print()
    finally:
        input("\nPresiona Enter para salir...")
