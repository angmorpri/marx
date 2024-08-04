# Python 3.10.11
# Creado: 30/07/2024
"""Herramienta para automatización de distribuciones monetarias

Presenta la clase 'Distribution', que permite automatizar la distribución de
dinero entre una fuente y uno o varios destinos, en función de una serie de
reglas predefinidas en archivos TOML conocidos como "criterios".

La clase se apoya en los modelos 'DistrSource' y 'DistrSink', que representan,
respectivamente, la fuente de dinero y los destinos del mismo.

"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import toml

from marx.models import Account, Counterpart, Category, Event, MarxDataStruct
from marx.util.factory import Factory


@dataclass
class DistrSource:
    """Fuente de la que nace la distribución monetaria

    Dispondrá de un origen o 'target', que puede ser una cuenta contable o una
    contraparte, y de una cantidad a distribuir, representada tanto de forma
    absoluta, como relativa al total de la cuenta.

    """

    target: Account | Counterpart
    amount: float
    ratio: float

    def __str__(self) -> str:
        return f"{self.target.repr_name}: {self.amount:.2f} € / {self.ratio:.2%}"


@dataclass
class DistrSink:
    """Destino de la distribución monetaria

    Dispondrá de un destino o 'target', que puede ser una cuenta contable o una
    contraparte, y de una cantidad a distribuir, representada tanto de forma
    absoluta, como relativa al total a distribuir. Si 'default' es True, la
    cantidad se calculará como la cantidad sobrante de lo distribuido.

    Además, dispone de todos los atributos necesarios para crear un evento
    contable: categoría, concept y detalles.

    Finalmente, los destinos también disponen de un nombre identificativo.

    """

    name: str
    target: Account | Counterpart
    default: bool
    amount: float
    ratio: float
    category: Category
    concept: str = ""
    details: str = ""

    def __str__(self) -> str:
        if self.default:
            money = "DEFAULT"
        elif self.amount != 0:
            money = f"{self.amount:.2f} €"
        else:
            money = f"{self.ratio:.2%}"
        return f"[{self.name}] -> {self.target.repr_name}: {money}; {self.category.code}; {self.concept!r}"


class Distribution:
    """Gestor de distribuciones monetarias

    El constructor recibe la estructura de datos Marx que se esté usando, la
    ruta de un archivo de criterios, y la fecha en la que se realiza la
    distribución. Del archivo de criterios se extraen las reglas, y, si no hay
    ningún error, se puede ejecutar el método 'run' para llevar a cabo la
    distribución y generar los eventos contables pertinentes. Estos eventos
    contables generados serán almacenados en la estructura de datos
    directamente.

    """

    def __init__(self, data: MarxDataStruct, criteria: Path, date: datetime):
        self.data = data
        self.criteria = criteria
        self.date = date
        self.parse()

    def parse(self) -> None:
        """Extrae las reglas de distribución del archivo de criterios"""
        criteria = toml.load(self.criteria)

        # Fuente
        if "source" not in criteria:
            raise ValueError("[Distr] No se ha especificado una fuente")
        source = criteria["source"]
        if "target" not in source:
            raise ValueError("[DistrSource] No se ha especificado un objetivo")
        target = source["target"]
        if target.startswith("@"):
            target = self.data.accounts.subset(repr_name=target).pullone()
            if target is None:
                raise ValueError(f"[DistrSource] La cuenta {source['target']!r} no existe")
            incomes = sum(
                self.data.events.subset(lambda x: x.date <= self.date, dest=target).amount
            )
            expenses = sum(
                self.data.events.subset(lambda x: x.date <= self.date, orig=target).amount
            )
            total = round(incomes - expenses, 2)
            if "amount" in source:
                amount = source["amount"]
                if amount > total:
                    raise ValueError(
                        "[DistrSource] La cantidad a distribuir supera la cantidad disponible en la cuenta"
                    )
                ratio = amount / total
            elif "ratio" in source:
                ratio = source["ratio"]
                amount = total * ratio
            else:
                raise ValueError(
                    "[DistrSource] No se ha especificado ni cantidad ni ratio a distribuir"
                )
        else:
            if "amount" in source:
                amount = source["amount"]
                ratio = 1
            elif "ratio" in source:
                raise ValueError("[DistrSource] No se puede usar ratio con un objetivo contraparte")
            else:
                raise ValueError(
                    "[DistrSource] No se ha especificado ni cantidad ni ratio a distribuir"
                )
        if amount == 0 or ratio == 0:
            raise ValueError("[DistrSource] La cantidad o el ratio no pueden ser 0")
        self.source = DistrSource(target, amount, ratio)

        # Destinos
        if "sinks" not in criteria:
            raise ValueError("[Distr] No se han especificado destinos")
        raw_sinks = criteria["sinks"]
        defaults = {key: value for key, value in raw_sinks.items() if not isinstance(value, dict)}
        raw_sinks = [(name, sink) for name, sink in raw_sinks.items() if isinstance(sink, dict)]
        self.sinks = []
        for name, raw_sink in raw_sinks:
            raw_sink = {**defaults, **raw_sink}
            if "target" not in raw_sink:
                raise ValueError(f"[DistrSink {name!r}] No se ha especificado un objetivo")
            target = raw_sink["target"]
            if target.startswith("@"):
                target = self.data.accounts.subset(repr_name=target).pullone()
                if target is None:
                    raise ValueError(
                        f"[DistrSink {name!r}] La cuenta {raw_sink['target']!r} no existe"
                    )
                if target == self.source.target:
                    raise ValueError(
                        f"[DistrSink {name!r}] El objetivo del destino no puede ser el objetivo de la fuente"
                    )
            if "amount" in raw_sink:
                amount = raw_sink["amount"]
                if amount > self.source.amount:
                    raise ValueError(
                        f"[DistrSink {name!r}] La cantidad a distribuir supera la cantidad disponible en la fuente"
                    )
                else:
                    ratio = 0
            elif "ratio" in raw_sink:
                ratio = raw_sink["ratio"]
                amount = 0
            else:
                raise ValueError(
                    f"[DistrSink {name!r}] No se ha especificado ni cantidad ni ratio a distribuir"
                )
            default = bool(raw_sink.get("default", False))
            if "category" not in raw_sink:
                raise ValueError(f"[DistrSink {name!r}] No se ha especificado una categoría")
            category = self.data.categories.subset(code=raw_sink["category"]).pullone()
            if category is None:
                raise ValueError(
                    f"[DistrSink {name!r}] La categoría {raw_sink['category']!r} no existe"
                )
            sink = DistrSink(
                name,
                target,
                default,
                amount,
                ratio,
                category,
                raw_sink.get("concept", ""),
                raw_sink.get("details", ""),
            )
            self.sinks.append(sink)

        # Comprobación de que la distribución es válida
        if not self.sinks:
            raise ValueError("[Distr] No se han especificado destinos")
        if sum(sink.default for sink in self.sinks) > 1:
            raise ValueError("[Distr] No puede haber más de un destino por defecto")
        if sum(sink.amount for sink in self.sinks) > self.source.amount:
            total = sum(sink.amount for sink in self.sinks)
            raise ValueError(
                f"[Distr] El total de cantidades recibidas por los sumideros ({total:.2f})"
                f" supera la cantidad indicada para distribuir ({self.source.amount:.2f})"
            )
        if any(sink.ratio > 0 for sink in self.sinks):
            if self.source.amount - sum(sink.amount for sink in self.sinks) <= 0:
                raise ValueError("[Distr] Existen destinos con ratio que no recibirán nada")

    def run(self) -> Factory[Event]:
        """Ejecuta la distribución monetaria

        En primer lugar, reparte las cantidades fijas, y luego, sobre el resto,
        reparte según los ratios. Si el resultado tras repartir no es 0, se
        añade o resta al destino marcado por defecto, si lo hay. Finalmente,
        se generan los eventos contables correspondientes.

        """
        remaining = self.source.amount
        events = self.data.events.subset()
        default_event = None
        for sink in sorted(self.sinks, key=lambda x: x.amount, reverse=True):
            if sink.amount > 0:
                amount = round(sink.amount, 2)
            else:
                amount = round(self.source.amount * sink.ratio, 2)
            remaining -= amount
            event = self.data.events.new(
                -1,
                date=self.date,
                amount=amount,
                category=sink.category,
                orig=self.source.target,
                dest=sink.target,
                concept=sink.concept,
                details=sink.details,
            )
            events.join(event)
            if sink.default:
                default_event = event
        # Ajuste en función de la cantidad restante
        if default_event and remaining != 0:
            default_event.amount = round(default_event.amount + remaining, 2)
        return events

    def __str__(self) -> str:
        s = f"SOURCE: {self.source}\n"
        s += "SINKS:\n"
        for sink in self.sinks:
            s += f"  - {sink}\n"
        return s
