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

import sqlite3 as sqlite
from collections import namedtuple
from pathlib import Path

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
        with sqlite.connect(self.db_path) as conn:
            conn.row_factory = sqlite.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM accounts")
            accounts = cursor.fetchall()
            cursor.execute("SELECT * FROM categories")
            categories = cursor.fetchall()
            cursor.execute("SELECT * FROM notes")
            notes = cursor.fetchall()
            cursor.execute("SELECT * FROM recurring")
            recurring = cursor.fetchall()
            cursor.execute("SELECT * FROM transactions")
            transactions = cursor.fetchall()
            cursor.execute("SELECT * FROM transfers")
            transfers = cursor.fetchall()
        self.suite = RawAdapterSuite(
            accounts=accounts,
            categories=categories,
            notes=notes,
            recurring=recurring,
            transactions=transactions,
            transfers=transfers,
        )
        return self.suite
