# 3.10.11
# Creado: 29/02/2024
"""Módulo para generar informes de balance general de cuentas."""

from datetime import datetime
from pathlib import Path
from typing import Iterable, Literal

from matplotlib.pylab import f

from marx.model import MarxDataSuite
from marx.reporting import TableBuilder
from marx.util.excel import ExcelManager, CellID, StylesCatalog, Formula


STYLES_PATH = Path(__file__).parents[2] / "config" / "styles.xlsx"

PADDING = 50
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
        timetable = {f"{date:%Y-%m-%d}": date for date in sorted(dates)}
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
            return self._report_text(table, output)

        elif format == "excel":
            return self._report_excel(table, Path(output), sheet)
            # Agrupación
            # if prev_node and prev_node.generation != 1:
            #    gen_diff = prev_node.generation - node.generation
            #    if gen_diff >= 3:
            #        excel.current_sheet.group_rows(
            #            prev_node.parent.parent.parent.row,
            #            prev_node.row,
            #            prev_node.generation - 3,
            #        )
            #    if gen_diff >= 2:
            #        excel.current_sheet.group_rows(
            #            prev_node.parent.parent.row, prev_node.row, prev_node.generation - 2
            #        )
            #    if gen_diff >= 1:
            #        excel.current_sheet.group_rows(
            #            prev_node.parent.row, prev_node.row, prev_node.generation - 1
            #        )
            # Continuación

    # Métodos para reporte específicos
    def _report_text(self, table: TableBuilder, output: Path | None) -> Path | None:
        """Reporte en formato texto."""
        # Cabecera
        headers = "  |".join(f"{header:>12}" for header in table.headers)
        text = [" " * PADDING + headers]

        # Cuerpo
        prev = None
        for node in table:
            # Totales al finalizar un nivel
            if prev and prev.gen > node.gen:
                summarizing_node = prev.parent
                for _ in range(prev.gen - node.gen):
                    indent = INDENT_SIZE * (summarizing_node.gen - 1)
                    if not summarizing_node.has_grandchildren():
                        line = self._values_line(
                            "", summarizing_node.values.values(), PADDING - indent
                        )
                        jump = ""
                    else:
                        line = self._values_line(
                            f"Total de {summarizing_node.title.lower()}",
                            summarizing_node.values.values(),
                            PADDING - indent,
                        )
                        jump = "\n"
                    text.append(jump + " " * indent + line)
                    summarizing_node = summarizing_node.parent
            # Títulos y valores principales
            indent = INDENT_SIZE * (node.gen - 1)
            if node.has_children():
                text.append(f"\n{' ' * indent}[{node.title}]")
            else:
                padding = PADDING - indent
                line = self._values_line(node.title, node.values.values(), padding)
                text.append(f"{' ' * indent}{line}")
            prev = node

        # Salida
        text = "\n".join(text)
        if output:
            with open(output, "w", encoding="utf-8") as file:
                file.write(text)
            return output
        print(text)

    def _values_line(self, title: str, values: Iterable[float], padding: int) -> str:
        sep = "." if title else " "
        str_values = []
        for value in values:
            value = f"{value:>,.2f}".replace(",", " ").replace(".", ",")
            str_values.append(f"{value:{sep}>10} €")
        str_values = (sep * 3).join(str_values)
        return f"{title:{sep}<{padding}}{str_values}"

    def _report_excel(self, table: TableBuilder, output: Path, sheet: int | str) -> Path:
        """Reporte en format Excel."""
        # Creación / Apertura de archivo
        manager = ExcelManager(output)
        styles = StylesCatalog(STYLES_PATH)
        STYLE = styles.pastel
        manager.sheets[sheet].select().clear()
        manager.current_sheet.set_column_width(1, 35)

        # Cabecera
        pointer = manager.pointer(at="A1")
        pointer.cell.value = table.title
        pointer.cell.style = STYLE.text.title
        pointer.right()
        for header in table.headers:
            pointer.cell.value = header
            pointer.cell.style = STYLE.text.date
            manager.current_sheet.set_column_width(pointer.column, 15)
            pointer.right()

        # Asignación de filas a nodos
        for row, node in enumerate(table, start=2):
            node.row = row

        # Cuerpo
        keys = [None] + list(table.headers)
        for node in table:
            pointer.goto((1, node.row))
            for col, key in enumerate(keys, start=1):
                # Valores
                if col == 1:
                    pointer.cell.value = node.title
                elif node.formula is None:
                    pointer.cell.value = node.values[key]
                elif node.formula == "@SUM_CHILDREN":
                    cells = [CellID((col, child.row)) for child in node]
                    pointer.cell.value = Formula("SUM", cells).build()
                # Estilos
                pointer.cell.style = STYLE["text" if col == 1 else "values"][f"h{node.gen}"]
                if node.title == "Pasivos":
                    pointer.cell.style.color.theme -= 2
                elif node.title == "Patrimonio neto":
                    pointer.cell.style.color.theme += 2
                # Movimiento
                pointer.right()

        # Formato y guardado
        manager.stylize()
        manager.save()
        manager.close()
        return output
