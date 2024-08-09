# Python 3.10.11
# Creado: 28/06/2024
"""Utilidades varias."""

from pathlib import Path


def safely_rename_file(path: Path, prefix: str) -> Path:
    """Renombra un archivo de forma segura.

    El nombre del nuevo archivo será "{prefix}{nombre_original}". Si dicho
    archivo ya existe, se añadirá un índice numérico al final del nombre,
    empezando por 1, antes de la extensión. Alternativamente, si "prefix"
    incluye el marcador "$", este será reemplazado por el índice. Dicho
    marcador se ignora si el índice fuera 1.

    Devuelve la ruta del archivo renombrado.

    """
    base = prefix + path.stem
    if "$" not in base:
        base += "$"
    # Intento inicial, '$' -> ''
    new = path.with_name(base.replace("$", "", 1) + path.suffix)
    if not new.exists():
        return new
    # Intentos sucesivos, '$' -> '1', '2', ...
    i = 2
    while True:
        new = path.with_name(base.replace("$", str(i), 1) + path.suffix)
        if not new.exists():
            return new
        i += 1


if __name__ == "__main__":
    p = Path(__file__).parent / "test.txt"
    p.touch()

    # MOD_
    print("MOD_")
    n1 = safely_rename_file(p, "MOD_")
    print("  1a vez:", n1)
    n1.touch()
    n2 = safely_rename_file(p, "MOD_")
    print("  2a vez:", n2)
    n2.touch()

    # MOD$_
    print("MOD$_")
    n3 = safely_rename_file(p, "MOD$_")
    print("  1a vez:", n3)
    n3.touch()
    n4 = safely_rename_file(p, "MOD$_")
    print("  2a vez:", n4)
    n4.touch()

    # Clean up
    p.unlink()
    n1.unlink()
    n2.unlink()
    n3.unlink()
    n4.unlink()
