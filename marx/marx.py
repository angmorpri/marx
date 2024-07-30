# Python 3.10.11
# Creado: 28/06/2024
"""API principal

Se presenta como una clase "Marx" que hay que instanciar para poder usarla.

"""

from datetime import datetime
from pathlib import Path
from typing import Any

from marx.automation import Distribution
from marx.mappers import MarxMapper

Report = dict[str, Any]


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

    - report: Genera diversos reportes en función de una serie de reglas
        predefinidas.

    El constructor no recibe argumentos.

    """

    def __init__(self) -> None:
        self.dbg_mode = False

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

    def distr(self, criteria: Path, date: datetime) -> Report:
        """Ejecuta distribuciones monetarias automáticas, en función del
        juego de reglas proporcionado.

        Los eventos generados se registrarán en la base de datos con la fecha
        indicada.

        Devuelve un reporte en forma de diccionario con los resultados
        obtenidos y las acciones realizadas.

        """
        d = Distribution(self.data, criteria, date)
        print(d)
        events = d.run()
        for event in events:
            print(event)

    def paycheck_parse(self, paycheck: Path, date: datetime) -> Report:
        """Analiza y extrae información de una nómina con formato predefinido.

        Los eventos generados se registrarán en la base de datos con la fecha
        indicada.

        Devuelve un reporte en forma de diccionario con los resultados
        obtenidos y las acciones realizadas.

        """
        raise NotImplementedError

    def loans_list(self, date_from: datetime, date_to: datetime) -> Report:
        """Identifica y devuelve los préstamos en el intervalo de fechas
        proporcionado.

        Devuelve un reporte en forma de diccionario con los resultados
        obtenidos y las acciones realizadas.

        """
        raise NotImplementedError

    def loans_default(self, loan_id: int, date: datetime) -> Report:
        """Genera una situación de impago en un préstamo.

        Los eventos generados se registrarán en la base de datos con la fecha
        indicada.

        Devuelve un reporte en forma de diccionario con los resultados
        obtenidos y las acciones realizadas.

        """
        raise NotImplementedError
