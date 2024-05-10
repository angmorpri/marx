# Python 3.10.11
# Creado: 10/05/2024
"""Gestor de rutas dinámicas.

Presenta una clase "Pathfinder", que utiliza archivos de configuración para
gestionar rutas dinámicas necesarias para otros archivos relevantes para el
programa.

"""

import configparser
import os

from pathlib import Path


class Pathfinder:
    """Gestor de rutas dinámicas.

    Permite gestionar, de manera centralizada, todas las rutas necesarias para
    que el programa funcione correctamente. Para ello, se basa en un archivo
    de configuración inicial, que contiene rutas y directorios a otros archivos
    referenciados mediante claves comunes que luego se pueden utilizar por
    los diferentes módulos del programa.

    Los métodos principales son:
    - request: Devuelve la ruta de un archivo dado su nombre clave.
    - resolve: Dada una ruta absoluta o relativa, devuelve el archivo adecuado,
        buscándolo tanto en el directorio del usuario como en el por defecto.

    Al instanciar la clase, se comprueba el archivo de rutas. Este debe tener
    formato INI con una única sección "paths". Si alguna de estas claves es
    "user-dir", comprobará si existe y es accesible. En caso de no existir, se
    creará.

    Recibe como parámetro la ruta al archivo de gestión de rutas principal, que
    debe tener formato INI. Se considerará que el directorio por defecto para
    archivos será aquél del archivo principal. Si se quiere indicar otro,
    puede hacerse mediante el parámetro "default_dir".

    """

    def __init__(self, base: str | Path, *, default_dir: str | Path | None = None):
        self.base = Path(base)
        if not self.base.exists():
            raise FileNotFoundError(f"No se encontró el archivo '{self.base}'")
        else:
            cfg = configparser.RawConfigParser()
            cfg.read(self.base, encoding="utf-8")
            if "paths" not in cfg.sections():
                raise configparser.NoSectionError("No se encontró la sección 'paths'")
            if "user-dir" in cfg["paths"]:
                user_dir = Path(os.path.expandvars(cfg["paths"]["user-dir"].strip('"')))
                if not user_dir.exists():
                    user_dir.mkdir(parents=True, exist_ok=True)
        self.default_dir = Path(default_dir or self.base.parent)

    def request(self, section: str, *, errors: bool = True) -> Path | None:
        """Devuelve la ruta de un archivo dado su nombre clave.

        Si la clave no existe o hay algún error con la ruta, se lanzarán las
        excepciones pertinentes. Si se quiere evitar esto, se puede indicar
        poniendo el parámetro "errors" a False, con lo que se devolverá None
        en caso de error.

        """
        cfg = configparser.RawConfigParser()
        cfg.read(self.base, encoding="utf-8")
        try:
            path = cfg.get("paths", section).strip('"')
        except configparser.NoOptionError:
            if errors:
                raise KeyError(f"No se encontró la clave '{section}'")
            return None
        return self.resolve(path, errors=errors)

    def resolve(self, path: str | Path, *, errors: bool = True) -> Path | None:
        """Resuelve una ruta dada, devolviendo el archivo correspondiente.

        Si la ruta es absoluta, comprueba que existe, y la devuelve.

        Si la ruta es relativa, intenta buscar el archivo en el directorio del
        usuario, si existe y es accesible; si no, busca en el directorio por
        defecto.

        Por defecto, si no hay algún problema con la ruta o el archivo, se
        lanzarán las excepciones adecuadas. Si se quiere evitar esto, se puede
        indicar poniendo el parámetro "errors" a False, con lo que se devolverá
        None en caso de error.

        """
        basepath = Path(os.path.expandvars(path))
        path = basepath
        if not path.is_absolute():
            user_dir = self.request("user-dir", errors=False)
            if user_dir.exists():
                path = user_dir / path
                if path.exists():
                    return path
            path = self.default_dir / basepath
        if not path.exists():
            if errors:
                raise FileNotFoundError(f"No se encontró el archivo '{path}'")
            return None
        return path
