# 3.10.11
# Creado: 29/02/2024
"""Módulo para generar informes de balance general de cuentas."""

from datetime import datetime
from pathlib import Path
from typing import Iterable, Literal

from marx.model import MarxDataSuite
from marx.reporting import TableBuilder, TableRow
from marx.reporting.excel import Excel, CellID, StylesCatalog


AMOUNT_PADDING = 50
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
        table.append("Activos", formula="@SUM_CHILDREN")
        table["Activos"].append("COR", "Activos corrientes", formula="@SUM_CHILDREN")
        table["Activos"].append("FIN", "Activos financieros", formula="@SUM_CHILDREN")

        for event in self.suite.events.search(status="closed"):
            for account, sign in zip((event.orig, event.dest), (-1, 1)):
                if isinstance(account, str) or account.unknown:
                    continue
                if account.name == "Inversión":
                    t1 = "FIN"
                    t2 = event.category.title
                    t2_order = event.category.code
                    t3 = event.concept
                elif account.name in ("Hucha", "Reserva"):
                    t1 = "COR"
                    t2 = "Ahorro y Reserva"
                    t2_order = 2
                    t3 = account.name
                else:
                    t1 = "COR"
                    t2 = "Caja"
                    t2_order = 1
                    t3 = account.name
                table[t1].append(t2, formula="@SUM_CHILDREN", order_key=t2_order)
                target = table[t1][t2].append(t3)
                for key, datelimit in timetable.items():
                    if event.date <= datelimit:
                        target.values[key] += sign * event.amount

        table.append("Pasivos", formula="@SUM_CHILDREN")
        table["Pasivos"].append("Deudas")

        table.append("PN", "Patrimonio neto", formula="@SUM_CHILDREN")
        table["PN"].append("Capital")
        # table["PN"].append("Capital", formula="{Activos} - {Pasivos}")
        for key, datelimit in timetable.items():
            table["PN"]["Capital"].values[key] = (
                table["Activos"].values[key] - table["Pasivos"].values[key]
            )
        return table

    def report(
        self,
        table: TableBuilder,
        format: Literal["text", "csv", "excel"] = "text",
        output: str | Path | None = None,
        *,
        sheet: int | str = 0,
    ) -> Path | None:
        """Genera un informe de balance general dado un objeto TableBuilder.

        Los formatos válidos son:
            - "text": texto plano. Si no se proporciona un valor para 'output',
                el informe se imprimirá en la consola.
            - "csv": archivo CSV. Requiere un valor para 'output'.
            - "excel": archivo Excel. Requiere un valor para 'output' y,
                opcionalmente, un valor para 'sheet' que puede ser el índice de
                la página (empezando por 0) o el nombre de la página.

        Devuelve la ruta del archivo generado, o None si no se generó ningún
        archivo.

        """
        if format in ("csv", "excel") and not output:
            raise ValueError(f"El formato '{format}' requiere un valor para 'output'.")

        if format == "text":
            headers = "  |".join(f"{header:>12}" for header in table.headers)
            text = [" " * AMOUNT_PADDING + headers]
            for node in table:
                text = self._text_report_line(node, text, 0)
            text = "\n".join(text)
            if output:
                with open(output, "w", encoding="utf-8") as file:
                    file.write(text)
                return Path(output)
            else:
                print(text)
                return None

        elif format == "excel":
            # Catálogo de estilos
            path = Path(__file__).parents[2] / "config" / "styles.xlsx"
            styles = StylesCatalog(path)
            # Primero, a cada nodo se le asigna una fila, que será aquélla en
            # la que le tocará escribir sus valores.
            for row, node in enumerate(table, start=2):
                node.row = row
            excel = Excel(output)
            excel.sheets[sheet].select()
            excel.current_sheet.set_column_width(1, 35)
            # Cabeceras
            pointer = excel.pointer(at="A1")
            pointer.cell.value = table.title
            pointer.right()
            for header in table.headers:
                pointer.cell.value = header
                excel.current_sheet.set_column_width(pointer.column, 15)
                pointer.right()
            # Contenido
            pointer.goto("A2")
            for node in table:
                pointer.cell.value = node.title
                pointer.cell.style = styles.pastel.text[f"h{node.generation}"]
                vp = pointer.copy()
                for col, header in enumerate(table.headers, start=2):
                    vp.right()
                    if node.formula is None:
                        vp.cell.value = node.values[header]
                    elif node.formula == "@SUM_CHILDREN":
                        sum_cells = [CellID((col, child.row)) for child in node]
                        vp.cell.value = excel.compose_formula("SUM", sum_cells)
                    vp.cell.style = styles.pastel.values[f"h{node.generation}"]
                pointer.down()
            excel.stylize()
            excel.save()
            excel.close()
            return output

    # Métodos para reporte en formato texto
    def _text_report_line(self, node: TableRow, text: list[str], indent_level: int) -> list[str]:
        """Genera una línea de texto para un informe en formato texto."""
        indent = indent_level * INDENT_SIZE
        if node.has_children():
            text.append(f"\n{indent * ' '}[{node.title}]")
            for child in node:
                text = self._text_report_line(child, text, indent_level + 1)
            if node.has_grandchildren() or indent_level == 0:
                title = f"Total {node.title.lower()}"
                jumps = 1
            else:
                title = ""
                jumps = 0
            text.append(self._balance_line(title, node.values.values(), indent_level, jumps))
            if indent_level == 0:
                text.append("\n-")
        else:
            text.append(self._balance_line(node.title, node.values.values(), indent_level))
        return text

    def _balance_line(
        self, title: str, values: Iterable[float], indent_level: int, jumps: int = 0
    ) -> str:
        """Genera una línea de balance para un informe en formato texto."""
        sep = "." if title else " "
        indent = indent_level * INDENT_SIZE
        padding = AMOUNT_PADDING - indent
        amounts = []
        for value in values:
            amounts.append(f"{self._amount_line(value):{sep}>10} €")
        amounts = (sep * 3).join(amounts)
        return ("\n" * jumps) + f"{indent * ' '}{title:{sep}<{padding}}{amounts}"

    def _amount_line(self, value: float) -> str:
        """Genera una línea de cantidad para un informe en formato texto."""
        return f"{value:>,.2f}".replace(",", " ").replace(".", ",")
