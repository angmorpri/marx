# Python 3.10.11
# Creado: 09/08/2024
"""Controlador sencillo para la configuración de usuario

La configuración de usuario para Marx se configura como un archivo TOML. Este
módulo presenta la clase 'UserConfig', que permite cargar dicha configuración y
extraer la información pertinente.

"""

from pathlib import Path
from typing import Any

import toml


class UserConfig:
    """Controlador para la configuración de usuario

    Presenta el método 'get', que devuelve el valor de una clave especificada,
    lanzando un error en caso de no encontrarla. Castea automáticamente los
    datos en función de la terminación de la clave.

    El constructor recibe la ruta del archivo de configuración, que debe tener
    formato TOML.

    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self.config = toml.load(path)

    def get(self, key: str, *, safe: bool = True) -> Any:
        """Devuelve el valor de la clave 'key', en cualquier sección del
        archivo de configuración

        Si la clave no se encuentra, o se encuentra pero está vacía, se
        imprimirá el mensaje de error pertinentes y se devolverá el código de
        error. Esto se puede evitar indicando 'safe=False', en cuyo caso, no
        se mostrará ningún mensaje y se devolverá 'None'.

        Las claves terminadas en '_dir' o '_path' serán convertidas a objetos
        'Path' automáticamente.

        """
        res = None
        # ubicando la clave
        for field, value in self.config.items():
            if isinstance(value, dict):
                if key in value:
                    res = value[key]
                    break
            elif field == key:
                res = value
                break
        # no se ha encontrado
        else:
            if safe:
                raise KeyError(
                    f"No se ha encontrado la clave '{key}' en el archivo de configuración"
                )
            return None
        # está vacía
        if not res:
            if safe:
                raise ValueError(
                    f"La clave '{key}' aparece vacía en el archivo de configuración"
                )
            return None
        # cast
        if key.endswith("_dir") or key.endswith("_path"):
            return Path(res)
        return res
