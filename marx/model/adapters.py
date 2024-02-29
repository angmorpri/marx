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

RawDataSuite = namedtuple(
    "RawDataSuite",
    ["accounts", "categories", "notes", "recurring", "transactions", "transfers"],
)

MarxDataSuite = namedtuple("MarxDataSuite", ["accounts", "categories", "notes", "events"])


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

    def load(self) -> RawDataSuite:
        """Carga los datos de la base de datos.

        Devuelve una namedtuple con las colecciones de datos cargadas.

        """
        if self.suite:
            return self.suite

        self.suite = RawDataSuite(
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
            self.db_path = source.db_path
        else:
            self.source = RawAdapter(source)
            self.db_path = Path(source)
        self.suite = None

    def load(self) -> MarxDataSuite:
        """Carga los datos de la base de datos.

        Devuelve una namedtuple con las colecciones de datos cargadas.

        """
        if self.suite:
            return self.suite
        raw_suite = self.source.load()

        self.suite = MarxDataSuite(
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
                    unknown=True,
                )
            account = self.suite.accounts[raw_trans.acc_id]
            if account is None:
                account = self.suite.accounts.new(
                    raw_trans.acc_id,
                    f"UNKNOWN_{raw_trans.acc_id:02}",
                    unknown=True,
                )
            counterpart = raw_trans.payee_name
            if raw_trans.is_debit:
                orig = counterpart
                dest = account.entity
            else:
                orig = account.entity
                dest = counterpart
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
                orig = self.suite.accounts.new(
                    raw_trans.from_id, f"UNKNOWN_{raw_trans.from_id:02}", unknown=True
                )
            dest = self.suite.accounts[raw_trans.to_id]
            if dest is None:
                dest = self.suite.accounts.new(
                    raw_trans.to_id, f"UNKNOWN_{raw_trans.to_id:02}", unknown=True
                )
            maybe_cat, *rest = raw_trans.note.split("\n")
            if maybe_cat.startswith("[") and maybe_cat.endswith("]"):
                name = maybe_cat[1:-1]
                category = self.suite.categories.get(name=name)
                if category is None:
                    vname = "V" + name[1:]
                    category = self.suite.categories.get(name=vname)
                    if category is None:
                        category = self.suite.categories.new(
                            id=-999,
                            name=vname,
                            unknown=True,
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

        # Operaciones recurrentes
        for raw_trans in raw_suite.recurring:
            date = datetime.strptime(raw_trans.date, "%Y%m%d")
            amount = round(raw_trans.amount, 2)
            category = self.suite.categories[raw_trans.cat]
            if category is None:
                category = self.suite.categories.new(
                    raw_trans.cat,
                    f"X{raw_trans.cat:02}. UNKNOWN",
                    unknown=True,
                )
            account = self.suite.accounts[raw_trans.acc_id]
            if account is None:
                account = self.suite.accounts.new(
                    raw_trans.acc_id,
                    f"UNKNOWN_{raw_trans.acc_id:02}",
                    unknown=True,
                )
            counterpart = raw_trans.payee_name
            if raw_trans.is_debit:
                orig = counterpart
                dest = account.entity
            else:
                orig = account.entity
                dest = counterpart
            _c, *_d = raw_trans.note.split("\n")
            _c = _c.strip()
            _d = "\n".join(_d).strip()
            concept = _c if _c else "Sin concepto"
            details = _d if _d else ""
            status = "recurring"
            self.suite.events.new(
                id=raw_trans.id * 1j,
                date=date,
                amount=amount,
                category=category.entity,
                orig=orig,
                dest=dest,
                concept=concept,
                details=details,
                status=status,
            )

        return self.suite

    def save(
        self, path: str | Path | None = None, *, only_update: bool = True, prefix: str = "MOD"
    ) -> Path:
        """Guarda los datos en una base de datos SQLite3.

        Si no se proporciona ninguna ruta, se guarda en
        'MOD_<nombre original>[.db]'. Si se proporciona un Path, se guarda en
        éste. Si se proporciona una cadena, se guarda en la misma carpeta que
        el original, pero con el nuevo nombre dado. También se puede cambiar
        el prefijo por defecto ('MOD') por otro mediante el parámetro 'prefix'.

        Por defecto, solo se guardan los datos que han sido modificados desde
        la última carga. Si se quiere guardar todo, se debe pasar 'only_update'
        como False.

        En caso de que se hayan creado nuevos datos, al ser guardados se les
        asigna automáticamente el ID correspondiente.

        Devuelve la ruta completa del archivo guardado.

        """
        # Obtención de la ruta
        if path is None:
            path = self.db_path.parent / f"{prefix}_{self.db_path.name}"
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

            # Novedades
            # Cuentas
            acc_iids = []
            for iid, account in self.suite.accounts._new:
                if account.id != -1:
                    continue
                params = {
                    "acc_name": account.name,
                    "acc_initial": 0.0,
                    "acc_order": account.order,
                    "acc_is_closed": 0,
                    "acc_color": account.color,
                    "acc_is_credit": 0,
                    "acc_min_limit": 0.0,
                }
                cursor.execute(
                    f"INSERT INTO tbl_account ({', '.join(params.keys())}) "
                    f"VALUES ({', '.join(['?'] * len(params))})",
                    tuple(params.values()),
                )
                acc_iids.append(iid)
                account.id = cursor.lastrowid
            # Categorías
            cat_iids = []
            for iid, category in self.suite.categories._new:
                if category.id != -1:
                    continue
                if category.type != 0:
                    params = {
                        "category_name": category.name,
                        "category_icon": category.icon,
                        "category_color": category.color,
                        "category_is_inc": category.type == 1,
                    }
                    cursor.execute(
                        f"INSERT INTO tbl_cat ({', '.join(params.keys())}) "
                        f"VALUES ({', '.join(['?'] * len(params))})",
                        tuple(params.values()),
                    )
                    cat_iids.append(iid)
                    category.id = cursor.lastrowid
                else:
                    params = {
                        "note_text": f"[{category.name}]",
                        "note_payee_payer": -1,
                    }
                    cursor.execute(
                        f"INSERT INTO tbl_notes ({', '.join(params.keys())}) "
                        f"VALUES ({', '.join(['?'] * len(params))})",
                        tuple(params.values()),
                    )
                    cat_iids.append(iid)
                    category.id = -cursor.lastrowid
            # Notas
            note_iids = []
            for iid, note in self.suite.notes._new:
                if note.id != -1:
                    continue
                params = {
                    "note_text": note.text,
                    "note_payee_payer": ["note", "payee", "payer"].index(note.target),
                }
                cursor.execute(
                    f"INSERT INTO tbl_notes ({', '.join(params.keys())}) "
                    f"VALUES ({', '.join(['?'] * len(params))})",
                    tuple(params.values()),
                )
                note_iids.append(iid)
                note.id = cursor.lastrowid
            # Eventos
            event_iids = []
            for iid, event in self.suite.events._new:
                if event.id != -1:
                    continue
                if event.type == 0:
                    params = {
                        "trans_amount": event.amount,
                        "trans_from_id": event.orig.id,
                        "trans_to_id": event.dest.id,
                        "trans_date": event.date.strftime("%Y%m%d"),
                        "trans_note": f"[{event.category.name}]\n{event.concept}\n{event.details}".strip(),
                    }
                    cursor.execute(
                        f"INSERT INTO tbl_transfer ({', '.join(params.keys())}) "
                        f"VALUES ({', '.join(['?'] * len(params))})",
                        tuple(params.values()),
                    )
                    event_iids.append(iid)
                    event.id = -cursor.lastrowid
                else:
                    params = {
                        "exp_amount": event.amount,
                        "exp_cat": event.category.id,
                        "exp_acc_id": event.account.id,
                        "exp_payee_name": event.counterpart,
                        "exp_date": event.date.strftime("%Y%m%d"),
                        "exp_is_debit": 1 if event.type == 1 else 0,
                        "exp_note": f"{event.concept}\n{event.details}".strip(),
                    }
                    if event.status == "recurring":
                        params = {f"r_{key}": value for key, value in params.items()}
                        params.update(
                            {
                                "r_exp_remind_val": -1,
                                "r_exp_week_month": None,
                                "r_exp_end_date": "20300101",
                                "r_exp_freq": 1,
                                "r_exp_cycle": 2,
                            }
                        )
                        cursor.execute(
                            f"INSERT INTO tbl_r_transfer ({', '.join(params.keys())}) "
                            f"VALUES ({', '.join(['?'] * len(params))})",
                            tuple(params.values()),
                        )
                        event_iids.append(iid)
                        event.id = cursor.lastrowid * 1j
                    else:
                        params.update(
                            {
                                "exp_month": event.date.strftime("%Y%m"),
                                "exp_is_paid": 1 if event.status == "closed" else 0,
                                "exp_is_bill": 1 if event.isbill else 0,
                                "exp_remind_val": -1,
                                "exp_notify_date": None,
                                "exp_rec_id": event.rsource,
                            }
                        )
                        cursor.execute(
                            f"INSERT INTO tbl_trans ({', '.join(params.keys())}) "
                            f"VALUES ({', '.join(['?'] * len(params))})",
                            tuple(params.values()),
                        )
                        event_iids.append(iid)
                        event.id = cursor.lastrowid

            # Modificaciones (parcial o total)
            # Cuentas
            update = self.suite.accounts._changed if only_update else self.suite.accounts._active
            for iid, account, *extra in update:
                if iid in acc_iids:
                    continue
                changes = {}
                updating_attrs = extra[0] if extra else account.__dict__.keys()
                for attr in updating_attrs:
                    if attr == "name":
                        changes["acc_name"] = getattr(account, attr)
                    elif attr == "order":
                        changes["acc_order"] = getattr(account, attr)
                    elif attr == "color":
                        changes["acc_color"] = getattr(account, attr)
                cursor.execute(
                    f"UPDATE tbl_account "
                    f"SET {', '.join(f'{key} = ?' for key in changes.keys())} "
                    f"WHERE acc_id = ?",
                    (*changes.values(), account.rid),
                )
            # Categorías
            update = (
                self.suite.categories._changed if only_update else self.suite.categories._active
            )
            for iid, category, *extra in update:
                if iid in cat_iids:
                    continue
                changes = {}
                updating_attrs = extra[0] if extra else category.__dict__.keys()
                if category.type == 0:
                    for attr in updating_attrs:
                        if attr in ("name", "code", "title"):
                            changes["note_text"] = "[" + category.name + "]"
                    cursor.execute(
                        f"UPDATE tbl_notes"
                        f"SET {', '.join(f'{key} = ?' for key in changes.keys())} "
                        f"WHERE notey_id = ?",
                        (*changes.values(), -category.rid),
                    )
                else:
                    for attr in updating_attrs:
                        if attr in ("name", "code", "title"):
                            changes["category_name"] = category.name
                        elif attr == "icon":
                            changes["category_icon"] = getattr(category, attr)
                        elif attr == "color":
                            changes["category_color"] = getattr(category, attr)
                        elif attr == "type":
                            changes["category_is_inc"] = getattr(category, attr) == 1
                    cursor.execute(
                        f"UPDATE tbl_cat "
                        f"SET {', '.join(f'{key} = ?' for key in changes.keys())} "
                        f"WHERE category_id = ?",
                        (*changes.values(), category.rid),
                    )
            # Notas
            update = self.suite.notes._changed if only_update else self.suite.notes._active
            for iid, note, *extra in update:
                if iid in note_iids:
                    continue
                changes = {}
                updating_attrs = extra[0] if extra else note.__dict__.keys()
                for attr in updating_attrs:
                    if attr == "text":
                        changes["note_text"] = getattr(note, attr)
                    elif attr == "target":
                        changes["note_payee_payer"] = ["note", "payee", "payer"].index(
                            getattr(note, attr)
                        )
                cursor.execute(
                    f"UPDATE tbl_notes "
                    f"SET {', '.join(f'{key} = ?' for key in changes.keys())} "
                    f"WHERE note_id = ?",
                    (*changes.values(), note.rid),
                )
            # Eventos
            update = self.suite.events._changed if only_update else self.suite.events._active
            for iid, event, *extra in update:
                if iid in event_iids:
                    continue
                changes = {}
                updating_attrs = extra[0] if extra else event.__dict__.keys()
                if event.type == 0:
                    for attr in updating_attrs:
                        if attr == "amount":
                            changes["trans_amount"] = getattr(event, attr)
                        elif attr == "orig":
                            changes["trans_from_id"] = getattr(event, attr).rid
                        elif attr == "dest":
                            changes["trans_to_id"] = getattr(event, attr).rid
                        elif attr == "date":
                            changes["trans_date"] = getattr(event, attr).strftime("%Y%m%d")
                        elif attr in ("category", "concept", "details"):
                            new = (
                                f"[{event.category.name}]\n{event.concept}\n{event.details}".strip()
                            )
                            changes["trans_note"] = new
                    cursor.execute(
                        f"UPDATE tbl_transfer "
                        f"SET {', '.join(f'{key} = ?' for key in changes.keys())} "
                        f"WHERE trans_id = ?",
                        (*changes.values(), event.rid),
                    )
                else:
                    for attr in updating_attrs:
                        if attr == "amount":
                            changes["exp_amount"] = getattr(event, attr)
                        elif attr == "category":
                            changes["exp_cat"] = event.category.rid
                            changes["exp_is_debit"] = 1 if event.category.type == 1 else 0
                        elif attr == "orig":
                            if isinstance(event.orig, str):
                                changes["exp_payee_name"] = getattr(event, attr)
                            else:
                                changes["exp_acc_id"] = getattr(event, attr).rid
                        elif attr == "dest":
                            if isinstance(event.dest, str):
                                changes["exp_payee_name"] = getattr(event, attr)
                            else:
                                changes["exp_acc_id"] = getattr(event, attr).rid
                        elif attr == "date":
                            changes["exp_date"] = getattr(event, attr).strftime("%Y%m%d")
                        elif attr in ("concept", "details"):
                            new = f"{event.concept}\n{event.details}".strip()
                            changes["exp_note"] = new
                    if event.status == "recurring":
                        changes = {f"r_{key}": value for key, value in changes.items()}
                        cursor.execute(
                            f"UPDATE tbl_r_trans "
                            f"SET {', '.join(f'{key} = ?' for key in changes.keys())} "
                            f"WHERE r_exp_id = ?",
                            (*changes.values(), event.rid),
                        )
                    else:
                        for attr in updating_attrs:
                            if attr == "date":
                                changes["exp_month"] = getattr(event, attr).strftime("%Y%m")
                            elif attr == "status":
                                changes["exp_is_paid"] = 1 if event.status == "closed" else 0
                        cursor.execute(
                            f"UPDATE tbl_trans "
                            f"SET {', '.join(f'{key} = ?' for key in changes.keys())} "
                            f"WHERE exp_id = ?",
                            (*changes.values(), event.rid),
                        )

            # Datos eliminados
            for iid, account in self.suite.accounts._deleted:
                cursor.execute(f"DELETE FROM tbl_account WHERE acc_id = {account.rid}")
            for iid, category in self.suite.categories._deleted:
                if category.type == 0:
                    cursor.execute(f"DELETE FROM tbl_notes WHERE note_id = {category.rid}")
                else:
                    cursor.execute(f"DELETE FROM tbl_cat WHERE category_id = {category.rid}")
            for iid, note in self.suite.notes._deleted:
                cursor.execute(f"DELETE FROM tbl_notes WHERE notey_id = {note.rid}")
            for iid, event in self.suite.events._deleted:
                if event.type == 0:
                    cursor.execute(f"DELETE FROM tbl_transfer WHERE trans_id = {event.rid}")
                elif event.status == "recurring":
                    cursor.execute(f"DELETE FROM tbl_r_trans WHERE r_exp_id = {event.rid}")
                else:
                    cursor.execute(f"DELETE FROM tbl_trans WHERE exp_id = {event.rid}")

        return path
