# Python 3.10.11
# Creado: 28/06/2024
"""Mapeadores entre la base de datos y el modelo de Marx

Hay dos mapeadores: el crudo (BaseMapper) y el de Marx (MarxMapper). El crudo
maneja la base de datos AS-IS, sin transformaciones; el de Marx, que se genera
a través de este, transforma los datos.

Se presentan también dos estructuras de datos: para la base (BaseDataStruct) y
para Marx (MarxDataStruct). Estas agrupan las colecciones de datos de cada
modelo, haciendo más sencillo su manejo.

"""

import shutil
import sqlite3 as sqlite
from collections import namedtuple
from datetime import datetime
from itertools import chain
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import DEFAULT

from pydantic import Tag

from marx.factory import Factory
from marx.model import Account, Counterpart, Category, Event
from marx.util import safely_rename_file

BaseDataStruct = namedtuple(
    "BaseDataStruct", ["accounts", "categories", "notes", "recurring", "transactions", "transfers"]
)
MarxDataStruct = namedtuple("MarxDataStruct", ["accounts", "categories", "events"])


DB_TABLES_METADATA = {
    "tbl_account": {"target": "accounts", "prefixes": ["acc_"]},
    "tbl_cat": {"target": "categories", "prefixes": ["category_"]},
    "tbl_note": {"target": "notes", "prefixes": ["note_", "notey_"]},
    "tbl_r_trans": {"target": "recurring", "prefixes": ["r_exp_"]},
    "tbl_trans": {"target": "transactions", "prefixes": ["exp_"]},
    "tbl_transfer": {"target": "transfers", "prefixes": ["trans_"]},
}

TCAT_PREFIX = "[T"
DEFAULT_TCAT_CODE = "T14"


class BaseMapper:
    """Mapeador básico: DB -> BaseDataStruct

    Los métodos disponibles son 'load' y 'save'. Para guardar los datos, se
    deben haber cargado previamente. Llamadas sucesivas a 'load' resetearán
    las modificaciones realizadas.

    El constructor recibe la ubicación de la base de datos a cargar.

    """

    def __init__(self, path: Path) -> None:
        self.source = path
        self.dest = None  # Ubicación de destino cuando se guarden los datos
        self.data = None  # Estructura "BaseDataStruct"

    def load(self) -> BaseDataStruct:
        """Carga la base de datos pasada como argumento"""
        self.data = BaseDataStruct(
            accounts=Factory(SimpleNamespace),
            categories=Factory(SimpleNamespace),
            notes=Factory(SimpleNamespace),
            recurring=Factory(SimpleNamespace),
            transactions=Factory(SimpleNamespace),
            transfers=Factory(SimpleNamespace),
        )
        with sqlite.connect(self.source) as conn:
            conn.row_factory = sqlite.Row
            cursor = conn.cursor()
            for table, metadata in DB_TABLES_METADATA.items():
                target = getattr(self.data, metadata["target"])
                cursor.execute(f"SELECT * FROM {table}")
                for row in cursor.fetchall():
                    attrs = {}
                    for key in row.keys():
                        for prefix in metadata["prefixes"]:
                            attr = key.replace(prefix, "")
                            if attr != key:
                                break
                        attrs[attr] = row[key]
                    target.new(**attrs)
        return self.data

    def save(self) -> Path:
        """Guarda los datos previamente cargados con las modificaciones
        realizadas.

        Crea una copia del original, añadiendo el prefijo "MOD_" al nombre. Si
        existen varias modificaciones, se añadirá un índice también.

        Una vez guardada, devuelve la ruta del archivo.

        """
        self.dest = safely_rename_file(self.source, "MOD$_")
        shutil.copy(self.source, self.dest)

        with sqlite.connect(self.dest) as conn:
            cursor = conn.cursor()
            for table, metadata in DB_TABLES_METADATA.items():
                prefix = metadata["prefixes"][0]
                source = getattr(self.data, metadata["target"])
                # INSERT
                for item in source.get(id=-1):
                    params = item.__dict__
                    cursor.execute(
                        f"INSERT INTO {table} ({', '.join(params.keys())})"
                        f" VALUES ({', '.join(['?' for _ in params])})",
                        tuple(params.values()),
                    )
                    item.id = cursor.lastrowid
                # UPDATE (sólo cambios)
                for item in source.get(lambda x: x.id != -1).metaget(tag="CHANGED"):
                    fixed_changes = {}
                    for attr in item.metaget(key="changes"):
                        prefixed = f"{prefix}{attr}".replace("note_id", "notey_id")
                        fixed_changes[prefixed] = getattr(item, attr)
                    pkey = f"{prefix}id".replace("note_id", "notey_id")
                    fixed_changes.pop(pkey)
                    cursor.execute(
                        f"UPDATE {table} SET {', '.join([f'{k} = ?' for k in fixed_changes])}"
                        f" WHERE {pkey} = ?",
                        (*fixed_changes.values(), item.id),
                    )
                # DELETE
                for item in source.metaget(tag="DELETED"):
                    pkey = f"{prefix}id".replace("note_id", "notey_id")
                    cursor.execute(f"DELETE FROM {table} WHERE {pkey} = ?", (item.id,))

        return self.dest


class MarxMapper:
    """Mapeador de Marx: DB -> BaseDataStruct -> MarxDataStruct.

    Los métodos disponibles son 'load' y 'save'. Para guardar los datos, se
    deben haber cargado previamente. Llamadas sucesivas a 'load' resetearán
    las modificaciones realizadas.

    El constructor recibe la ubicación de la base de datos a cargar.

    """

    def __init__(self, path: Path) -> None:
        self.source = path
        self.dest = None  # Ubicación de destino cuando se guarden los datos
        self.data = None  # Estructura "MarxDataStruct"

    def load(self) -> MarxDataStruct:
        """Carga la base de datos pasada como argumento"""
        self.data = MarxDataStruct(
            accounts=Factory(Account),
            categories=Factory(Category),
            events=Factory(Event),
        )

        base = BaseMapper(self.source).load()

        # Cuentas
        for base_account in base.accounts:
            self.data.accounts.new(
                id=base_account.id,
                name=base_account.name,
                order=base_account.order,
                color=base_account.color,
            )

        # Categorías oficiales
        for base_category in base.categories:
            self.data.categories.new(
                id=base_category.id,
                name=base_category.name,
                icon=base_category.icon,
                color=base_category.color,
            )

        # Categorías que proceden de notas
        for note in base.notes.get(lambda x: x.text.strip().startswith(TCAT_PREFIX)):
            self.data.categories.new(
                id=-note.id,
                name=note.text.strip().split("\n")[0],
            )

        # Eventos de ingreso y gasto, y eventos recurrentes
        for base_trans in chain(base.transactions, base.recurring):
            date = datetime.strptime(base_trans.date, "%Y%m%d")
            amount = round(base_trans.amount, 2)
            category = self.data.categories.get(id=base_trans.cat)
            if category is None:
                category = self.data.categories.new(
                    id=base_category.id,
                    name=f"X{base_trans.cat:02}. UNKNOWN",
                    disabled=True,
                )
            account = self.data.accounts.get(id=base_trans.acc_id)
            if account is None:
                account = self.data.accounts.new(
                    id=base_trans.acc_id,
                    name=f"UNKNOWN_{base_trans.acc_id:02}",
                    disabled=True,
                )
            counterpart = Counterpart(base_trans.payee_name)
            if base_trans.is_debit:
                orig, dest = counterpart, account.pullone()
            else:
                orig, dest = account.pullone(), counterpart
            concept, *details = base_trans.note.split("\n")
            concept = concept.strip() or "Sin concepto"
            details = "\n".join(details).strip() or ""
            # Estándar / Recurrente
            if hasattr(base_trans, "is_bill"):
                event_id = base_trans.id
                status = Event.CLOSED if base_trans.is_paid else Event.OPEN
                rsource = base_trans.rec_id if base_trans.is_bill else -1
            else:
                event_id = 1j * base_trans.id
                status = Event.RECURRING
                rsource = -1
            self.data.events.new(
                id=event_id,
                date=date,
                amount=amount,
                category=category.pullone(),
                orig=orig,
                dest=dest,
                concept=concept,
                details=details,
                status=status,
                rsource=rsource,
            )

        # Eventos de traslados entre cuentas
        for base_trans in self.base.transfers:
            date = datetime.strptime(base_trans.date, "%Y%m%d")
            amount = round(base_trans.amount, 2)
            orig = self.data.accounts.get(id=base_trans.from_id)
            if orig is None:
                orig = self.data.accounts.new(
                    id=base_trans.from_id,
                    name=f"UNKNOWN_{base_trans.from_id:02}",
                    disabled=True,
                )
            dest = self.data.accounts.get(id=base_trans.to_id)
            if dest is None:
                dest = self.data.accounts.new(
                    id=base_trans.to_id,
                    name=f"UNKNOWN_{base_trans.to_id:02}",
                    disabled=True,
                )
            maybe_category, *rest = base_trans.note.split("\n")
            if maybe_category.startswith(TCAT_PREFIX):
                category_name = maybe_category[1:-1]
                category = self.data.categories.get(name=category_name)
                if category is None:
                    category = self.data.categories.new(
                        id=-999,
                        name=category_name,
                        disabled=True,
                    )
            else:
                category = self.data.categories.get(code=DEFAULT_TCAT_CODE)
                rest = [maybe_category] + rest
            concept = rest[0].strip() or "Sin concepto"
            details = "\n".join(rest[1:]).strip() or ""
            self.data.events.new(
                id=-base_trans.id,
                date=date,
                amount=amount,
                category=category.pullone(),
                orig=orig.pullone(),
                dest=dest.pullone(),
                concept=concept,
                details=details,
            )

    def save(self, *, update_all: bool = False) -> Path:
        """Guarda los datos previamente cargados con las modificaciones
        realizadas.

        Crea una copia del original, añadiendo el prefijo "MOD_" al nombre. Si
        existen varias modificaciones, se añadirá un índice también.

        Si 'update_all' es True, se actualizarán todos los registros, no sólo
        los que han sido modificados (por defecto).

        Una vez guardada, devuelve la ruta del archivo.

        """
        self.dest = safely_rename_file(self.source, "MOD$_")
        shutil.copy(self.source, self.dest)

        with sqlite.connect(self.dest) as conn:
            cursor = conn.cursor()
            # INSERT
            to_insert = []
            for factory in self.data.accounts, self.data.categories, self.data.events:
                for item in factory.get(id=-1):
                    to_insert.append([item, *item.serialize("db")])
            for item, table_name, _, params in to_insert:
                cursor.execute(
                    f"INSERT INTO {table_name} ({', '.join(params.keys())})"
                    f" VALUES ({', '.join(['?' for _ in params])})",
                    tuple(params.values()),
                )
                item.id = cursor.lastrowid

            # UPDATE
            to_update = []
            for factory in self.data.accounts, self.data.categories, self.data.events:
                factory = factory.get(lambda x: x.id != -1)  # No elementos nuevos
                factory = factory if update_all else factory.metaget(tag="CHANGED")
                for item in factory:
                    params_changed = {} if update_all else item.metaget(key="changes").keys()
                    to_update.append([item, *item.serialize("db", params_changed)])
            for item, table_name, table_pkey, params in to_update:
                cursor.execute(
                    f"UPDATE {table_name} SET {', '.join([f'{k} = ?' for k in params])}"
                    f" WHERE {table_pkey} = ?",
                    (*params.values(), item.id),
                )

            # DELETE
            to_delete = []
            for factory in self.data.accounts, self.data.categories, self.data.events:
                for item in factory.metaget(tag="DELETED"):
                    to_delete.append([item, *item.serialize("db")])
            for item, table_name, table_pkey, _ in to_delete:
                cursor.execute(f"DELETE FROM {table_name} WHERE {table_pkey} = ?", (item.id,))
