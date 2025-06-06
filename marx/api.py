# Python 3.10.11
# Creado: 28/06/2024
"""API principal

Se presenta como una clase "Marx" que hay que instanciar para poder usarla.

"""

from datetime import datetime
from pathlib import Path
from typing import Any

from marx.automation import Distribution, LoansHandler, PaycheckParser
from marx.models import MarxMapper
from marx.reporting import Report

Result = dict[str, Any]


class Marx:
    """API principal

    Presenta los métodos:

    - load: Para cargar una base de datos.
    - save: Para guardar los cambios en una nueva base de datos a partir de la
        original.

    - distr: Para ejecutar distribuciones monetarias automáticas basadas en
        reglas predefinidas.
    - paycheck_parse: Analiza y extrae información de una nómina con formato
        predefinido.
    - loans_list: Lista los préstamos en curso.
    - loans_default: Genera una situación de impago en un préstamo.

    - build_report: Crea un reporte en formato Excel, a partir de un generador
        (objeto de la clase Report) y unas fechas.

    El constructor no recibe argumentos.

    """

    def __init__(self) -> None:
        self.dbg_mode = False
        self.mapper = None
        self.data = None

    def load(self, path: Path) -> None:
        """Carga la base de datos"""
        self.mapper = MarxMapper(path)
        self.data = self.mapper.load()

    def save(self) -> Path:
        """Guarda los cambios en una nueva base de datos

        La nueva base de datos se crea con un nombre por defecto a partir de
        la primera, y se devuelve su ruta.

        """
        return self.mapper.save(dbg=self.dbg_mode)

    def distr(self, criteria: Path, date: datetime) -> Result:
        """Ejecuta distribuciones monetarias automáticas, en función del
        juego de reglas proporcionado.

        Los eventos generados se registrarán en la base de datos con la fecha
        indicada.

        Devuelve un reporte en forma de diccionario con los resultados
        obtenidos y las acciones realizadas.

        """
        d = Distribution(self.data, criteria, date)
        events = d.run()
        return {
            "date": d.date.strftime("%Y-%m-%d"),
            "source": {
                "target": d.source.target.serialize(),
                "amount": d.source.amount,
                "ratio": d.source.ratio,
            },
            "sinks": [
                {
                    "name": sink.name,
                    "target": sink.target.serialize(),
                    "default": sink.default,
                    "amount": sink.amount,
                    "ratio": sink.ratio,
                    "category": sink.category.serialize(),
                    "concept": sink.concept,
                    "details": sink.details,
                }
                for sink in d.sinks
            ],
            "events": [event.serialize() for event in events],
        }

    def paycheck_parse(self, paycheck: Path, criteria: Path, date: datetime) -> Result:
        """Analiza y extrae información de una nómina con formato predefinido.

        Los eventos generados se registrarán en la base de datos con la fecha
        indicada.

        Devuelve un reporte en forma de diccionario con los resultados
        obtenidos y las acciones realizadas.

        """
        parser = PaycheckParser(self.data, criteria)
        events = parser.parse(paycheck, date)
        return {
            "events": [event.serialize() for event in events],
        }

    def loans_list(self, date_to: datetime) -> Result:
        """Identifica y devuelve los préstamos en el intervalo de fechas
        proporcionado.

        Devuelve un reporte en forma de diccionario con los resultados
        obtenidos y las acciones realizadas.

        """
        handler = LoansHandler(self.data)
        loans = handler.find(date_to)
        return {
            loan.tag: {
                "position": loan.position,
                "status": loan.status,
                "start_date": loan.start_date.strftime("%Y-%m-%d"),
                "end_date": loan.end_date.strftime("%Y-%m-%d") if loan.end_date else "",
                "stop_date": date_to.strftime("%Y-%m-%d"),
                "amount": loan.amount,
                "paid": loan.paid,
                "remaining": loan.remaining,
                "counterparts": loan.counterparts,
                "events": [event.serialize() for event in loan.events],
            }
            for loan in loans
        }

    def loans_default(self, loan_tag: str) -> Result:
        """Genera una situación de impago en un préstamo."""
        handler = LoansHandler(self.data)
        events = handler.default(loan_tag)
        return {
            "events": [event.serialize() for event in events],
        }

    def build_report(
        self,
        report: Report,
        dates: list[datetime],
        output_path: Path,
        output_sheet: str,
    ) -> Path:
        """Genera un reporte a partir de un generador y sus parámetros"""
        report.prepare(output_path, output_sheet)
        report.build(dates)
        return report.save()
