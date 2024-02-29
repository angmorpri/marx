# 3.10.11
# Creado: 29/02/2024
"""Módulo para generar informes de balance general de cuentas."""

from datetime import datetime
from pathlib import Path
from typing import Literal

from marx.model import MarxDataSuite
from marx.reporting import TableBuilder


INDENT_SIZE = 4


class Balance:
    """Clase para generar balances generales de cuentas.

    Dados una serie de datos financieros y una o varias fechas, esta clase
    generará una tabla TableBuilder que representará un balance general
    contable para esas fechas, y que luego se puede presentar en un informe
    con diversos formatos.

    Los métodos proporcionados son:
        - build: genera la tabla de balance para una o varias fechas.
        - report: genera un informe de balance en diversos formatos.

    El constructor sólo requiere un objeto MarxAdapter que contenga los datos
    financieros necesarios.

    """

    def __init__(self, data: MarxDataSuite):
        self.suite = data

    def build(self, *dates: datetime) -> TableBuilder:
        """Genera una tabla de balance general para cada fecha dada.

        Devuelve la tabla creada como un objeto TableBuilder.

        """
        timetable = {f"{date:%Y-%m}": date for date in sorted(dates)}
        table = TableBuilder(headers=timetable.keys())
        table.append("Activos", values="SUM_CHILDREN")
        table["Activos"].append("COR", "Activos corrientes", values="SUM_CHILDREN")
        table["Activos"].append("FIN", "Activos financieros", values="SUM_CHILDREN")

        for event in self.suite.events.search(status="closed"):
            for account, sign in zip((event.orig, event.dest), (-1, 1)):
                if isinstance(account, str) or account.unknown:
                    continue
                if account.name == "Inversión":
                    t1 = "FIN"
                    t2 = event.category.title
                    t2_order = event.category.code
                    t3 = event.concept
                elif account.name in ("Ahorro", "Reserva"):
                    t1 = "COR"
                    t2 = "Ahorro y Reserva"
                    t2_order = 2
                    t3 = account.name
                else:
                    t1 = "COR"
                    t2 = "Caja"
                    t2_order = 1
                    t3 = account.name
                table[t1].append(t2, values="SUM_CHILDREN", order_key=t2_order)
                target = table[t1][t2].append(t3)
                for key, datelimit in timetable.items():
                    if event.date <= datelimit:
                        target.values[key] += sign * event.amount

        return table

    def report(
        self,
        table: TableBuilder,
        format: Literal["text", "csv", "excel"] = "text",
        output: str | Path | None = None,
    ) -> Path | None:
        """Genera un informe de balance general dado un objeto TableBuilder.

        Los formatos válidos son:
            - "text": texto plano. Si no se proporciona un valor para 'output',
                el informe se imprimirá en la consola.
            - "csv": archivo CSV. Requiere un valor para 'output'.
            - "excel": archivo Excel. Requiere un valor para 'output'.

        Devuelve la ruta del archivo generado, o None si no se generó ningún
        archivo.

        """
        if format in ("csv", "excel") and not output:
            raise ValueError(f"El formato '{format}' requiere un valor para 'output'.")

        if format == "text":
            _res = []
            for row in table:
                _res = self._text_report_line(row, _res, indent_level=0)
            text = "\n".join(_res)
            if output:
                with open(output, "w", encoding="utf-8") as file:
                    file.write(text)
                return Path(output)
            else:
                print(text)
                return None

    def _text_report_line(self, node, key, text, indent_level):
        """Genera una línea de texto para un informe en formato texto."""
        indent = indent_level * INDENT_SIZE
        if node.has_children():
            text.append(f"\n\n{indent}[{node.title}]")
            for child in node:
                text = self._text_report_line(child, key, text, indent_level + 1)
            if not node.has_grandchildren():
                title = ""
            else:
                title = f"Total {node.title.lower()}"
            text.append(self._balance_line(title, node.values[key], indent_level))
            if indent_level == 0:
                text.append("\n-")
        else:
            amount = self._amount_line(node.values[key])
            text.append(...)
        return text
