# Python 3.10.11
# Creado: 24/01/2024
"""Adaptadores del modelo de datos a la base de datos.

Marx utiliza como principal fuente de datos la base de datos SQLite3 que genera
la aplicación MiBilletera al realizar un backup de sus datos. Estos datos
pueden usarse en el programa de dos formas:

    - Crudos: No hay transformación alguna, se usan tal cual vienen de la base
        de datos. Sirve para hacer modificaciones seguras o urgentes, a costa
        de perder la abstracción del modelo de datos.
        
    - Adaptados: Se transforman los datos para que puedan ser usados por las
        herramientas principales de Marx, como los automatizadores de tareas
        o los reportes. Abstraen el modelo de datos, pero pueden ser más
        difíciles de modificar.
        
Las clases implementadas son, respectivamente, 'RawAdapter' y 'MarxAdapter'.
Ambas reciben como parámetro la ruta a la base de datos, cargan los datos
mediante el método 'load', y permiten volver a guardar con los cambios hechos
mediante el método 'save'.

Cada conjunto de datos de un mismo tipo se proporciona como un objeto de la
clase 'Collection'. Al usar 'load', se almacena internamente en una namedtuple
llamada 'suite'. Por ejemplo, para acceder a la colección de cuentas, se usaría
'adapter.suite.accounts'.

"""

import shutil
import sqlite3 as sqlite
from collections import namedtuple
from pathlib import Path
from types import SimpleNamespace

from marx.model import Collection


TABLES = {
    "tbl_account": ("accounts", "acc_"),  # (nombre destino, prefijos a eliminar)
    "tbl_cat": ("categories", "category_"),
    "tbl_notes": ("notes", "note_", "notey_"),
    "tbl_r_trans": ("recurring", "r_exp_"),
    "tbl_trans": ("transactions", "exp_"),
    "tbl_transfer": ("transfers", "trans_"),
}

RawAdapterSuite = namedtuple(
    "RawAdapterSuite",
    ["accounts", "categories", "notes", "recurring", "transactions", "transfers"],
)


class RawAdapter:
    """Adaptador de datos "en crudo" de la base de datos.

    Al cargar, presenta las siguientes colecciones en el atributo 'suite',
    cada uno correspondiente a una tabla de la base de datos:

        - accounts: Cuentas.
        - categories: Categorías.
        - notes: Notas.
        - recurring: Operaciones recurrentes.
        - transactions: Transacciones.
        - transfers: Transferencias.

    Todas estas colecciones se componen de instancias 'DefaultEntity', que
    mapean automáticamente los datos de cada tabla de la base de datos.

    """

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)

    def load(self) -> RawAdapterSuite:
        """Carga los datos de la base de datos.

        Devuelve una namedtuple con las colecciones de datos cargadas.

        """
        self.suite = RawAdapterSuite(
            accounts=Collection(SimpleNamespace, pkeys=["id"]),
            categories=Collection(SimpleNamespace, pkeys=["id"]),
            notes=Collection(SimpleNamespace, pkeys=["id"]),
            recurring=Collection(SimpleNamespace, pkeys=["id"]),
            transactions=Collection(SimpleNamespace, pkeys=["id"]),
            transfers=Collection(SimpleNamespace, pkeys=["id"]),
        )
        with sqlite.connect(self.db_path) as conn:
            conn.row_factory = sqlite.Row
            cursor = conn.cursor()
            for table, (name, *prefixes) in TABLES.items():
                cursor.execute(f"SELECT * FROM {table}")
                col = getattr(self.suite, name)
                for row in cursor.fetchall():
                    attrs = {}
                    for key in row.keys():
                        for prefix in prefixes:
                            attr = key.replace(prefix, "")
                            if attr != key:
                                break
                        attrs[attr] = row[key]
                    col.new(**attrs)
        return self.suite

    def save(self, path: str | Path | None = None, *, only_update: bool = True) -> Path:
        """Guarda los datos en una base de datos SQLite3.

        Si no se proporciona ninguna ruta, se guarda en
        'MOD_<nombre original>[.db]'. Si se proporciona un Path, se guarda en
        éste. Si se proporciona una cadena, se guarda en la misma carpeta que
        el original, pero con el nuevo nombre dado.

        Por defecto, solo se guardan los datos que han sido modificados desde
        la última carga. Si se quiere guardar todo, se debe pasar 'only_update'
        como False.

        En caso de que se hayan creado nuevos datos, al ser guardados se les
        asigna automáticamente el ID correspondiente.

        Devuelve la ruta completa del archivo guardado.

        """
        # Obtención de la ruta
        if path is None:
            path = self.db_path.parent / f"MOD_{self.db_path.name}"
            if not path.suffix:
                path = path.with_suffix(".db")
        elif isinstance(path, str):
            path = self.db_path.parent / path
        elif isinstance(path, Path):
            pass
        else:
            raise TypeError("La ruta debe ser un str o un Path.")

        # Copiamos la original en la nueva, para modificarla después
        shutil.copy(self.db_path, path)

        # Guardado de los datos
        with sqlite.connect(path) as conn:
            cursor = conn.cursor()
            for table, (name, *prefixes) in TABLES.items():
                prefix = prefixes[0]
                entities = getattr(self.suite, name)
                # Nuevos datos
                iids = []
                for iid, entity in entities._new:
                    if entity.id != -1:
                        continue
                    cursor.execute(
                        f"INSERT INTO {table} ({', '.join(entity.__dict__.keys())}) "
                        f"VALUES ({', '.join(['?'] * len(entity.__dict__))})",
                        tuple(entity.__dict__.values()),
                    )
                    iids.append(iid)
                    entity.id = cursor.lastrowid
                # Modificaciones (parcial o total)
                update = entities._changed if only_update else entities._active
                for iid, entity, *extra in update:
                    if iid in iids:
                        continue
                    updating_attrs = extra[0] if extra else entity.__dict__.keys()
                    changes = {}
                    for attr in updating_attrs:
                        pattr = prefix + attr
                        pattr = pattr.replace("note_id", "notey_id")
                        changes[pattr] = getattr(entity, attr)
                    pkey = (prefix + "id").replace("note_id", "notey_id")
                    changes.pop(pkey, None)
                    cursor.execute(
                        f"UPDATE {table} "
                        f"SET {', '.join(f'{key} = ?' for key in changes.keys())} "
                        f"WHERE {pkey} = ?",
                        (*changes.values(), entity.id),
                    )
                # Datos eliminados
                for iid, entity in entities._deleted:
                    pkey = (prefix + "_id").replace("note_id", "notey_id")
                    cursor.execute(f"DELETE FROM {table} WHERE {pkey} = {entity.id}")
