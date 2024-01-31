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
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from marx.model import Collection, Account, Category, Note, Event


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

MarxAdapterSuite = namedtuple("MarxAdapterSuite", ["accounts", "categories", "notes", "events"])


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

    Todas estas colecciones se componen de instancias 'SimpleNamespace', que
    mapean automáticamente los datos de cada tabla de la base de datos. Debido
    a ello, se tiene que tener en cuenta que no hay ningún tipo de validación
    de datos, por lo que si se modifican los datos de forma incorrecta, se
    pueden producir errores al guardarlos de nuevo.

    El constructor recibe la ruta a la base de datos.

    """

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.suite = None

    def load(self) -> RawAdapterSuite:
        """Carga los datos de la base de datos.

        Devuelve una namedtuple con las colecciones de datos cargadas.

        """
        if self.suite:
            return self.suite

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


class MarxAdapter:
    """Adaptador de datos al formato usado por Marx.

    Al cargar, presenta las siguientes colecciones en el atributo 'suite',
    que agregan de forma lógica los diferentes tipos de datos de la base:

        - accounts: Cuentas.
        - categories: Categorías.
        - notes: Notas.
        - events: Eventos. Esto incluye transacciones, transferencias y
            operaciones recurrentes.

    Cada una de ellas es una colección tipo 'Collection', cuya clase base es,
    respectivamente, 'Account', 'Category', 'Note' y 'Event'.

    El constructor puede recibir o bien la ruta a la base de datos, o bien un
    adaptador de datos en crudo tipo 'RawAdapter'.

    """

    def __init__(self, source: str | Path | RawAdapter):
        if isinstance(source, RawAdapter):
            self.source = source
        else:
            self.source = RawAdapter(source)
        self.suite = None

    def load(self) -> MarxAdapterSuite:
        """Carga los datos de la base de datos.

        Devuelve una namedtuple con las colecciones de datos cargadas.

        """
        if self.suite:
            return self.suite
        raw_suite = self.source.load()

        self.suite = MarxAdapterSuite(
            accounts=Collection(Account, pkeys=["id", "name"]),
            categories=Collection(Category, pkeys=["id", "code", "title", "name"]),
            notes=Collection(Note, pkeys=["id"]),
            events=Collection(Event, pkeys=["id"]),
        )

        # Cuentas
        for raw_account in raw_suite.accounts:
            self.suite.accounts.new(
                id=raw_account.id,
                name=raw_account.name,
                order=raw_account.order,
                color=raw_account.color,
            )

        # Categorías
        for raw_category in raw_suite.categories:
            self.suite.categories.new(
                id=raw_category.id,
                name=raw_category.name,
                icon=raw_category.icon,
                color=raw_category.color,
            )

        # Categorías de traslado (vienen de 'notes')
        for raw_note in raw_suite.notes.search(lambda x: x.text.strip().startswith("[T")):
            catname = raw_note.text.strip().split("\n")[0]
            self.suite.categories.new(
                id=-raw_note.id,
                name=catname[1:-1],
            )

        # Notas
        for raw_note in raw_suite.notes.search(lambda x: not x.text.strip().startswith("[T")):
            target = ["payee", "payer", "note"][raw_note.payee_payer]
            self.suite.notes.new(
                id=raw_note.id,
                text=raw_note.text,
                target=target,
            )

        # Transacciones
        for raw_trans in raw_suite.transactions:
            date = datetime.strptime(raw_trans.date, "%Y%m%d")
            amount = round(raw_trans.amount, 2)
            category = self.suite.categories[raw_trans.cat]
            if category is None:
                category = self.suite.categories.new(
                    raw_trans.cat,
                    f"X{raw_trans.cat:02}. UNKNOWN",
                )
            account = self.suite.accounts[raw_trans.acc_id]
            if account is None:
                account = self.suite.accounts.new(
                    raw_trans.acc_id,
                    f"UNKNOWN_{raw_trans.acc_id:02}",
                )
            counterpart = raw_trans.payee_name
            if raw_trans.is_debit:
                orig = account.entity
                dest = counterpart
            else:
                orig = counterpart
                dest = account.entity
            _c, *_d = raw_trans.note.split("\n")
            _c = _c.strip()
            _d = "\n".join(_d).strip()
            concept = _c if _c else "Sin concepto"
            details = _d if _d else ""
            status = "closed" if raw_trans.is_paid else "open"
            rsource = raw_trans.rec_id if raw_trans.is_bill else -1
            self.suite.events.new(
                id=raw_trans.id,
                date=date,
                amount=amount,
                category=category.entity,
                orig=orig,
                dest=dest,
                concept=concept,
                details=details,
                status=status,
                rsource=rsource,
            )

        # Traslados
        for raw_trans in raw_suite.transfers:
            date = datetime.strptime(raw_trans.date, "%Y%m%d")
            amount = round(raw_trans.amount, 2)
            orig = self.suite.accounts[raw_trans.from_id]
            if orig is None:
                orig = self.suite.accounts.new(raw_trans.from_id, f"UNKNOWN_{raw_trans.from_id:02}")
            dest = self.suite.accounts[raw_trans.to_id]
            if dest is None:
                dest = self.suite.accounts.new(raw_trans.to_id, f"UNKNOWN_{raw_trans.to_id:02}")
            maybe_cat, *rest = raw_trans.note.split("\n")
            if maybe_cat.startswith("[") and maybe_cat.endswith("]"):
                name = maybe_cat[1:-1]
                category = self.suite.categories.get(name=name)
                if category is None:
                    category = self.suite.categories.new(
                        id=-999,
                        name="V" + name[1:],
                    )
            else:
                category = self.suite.categories.get(code="T14")
                rest = [maybe_cat] + rest
            concept = rest[0].strip() if rest else "Sin concepto"
            details = "\n".join(rest[1:]).strip() if rest[1:] else ""
            self.suite.events.new(
                id=-raw_trans.id,
                date=date,
                amount=amount,
                category=category.entity,
                orig=orig.entity,
                dest=dest.entity,
                concept=concept,
                details=details,
            )

        return self.suite
