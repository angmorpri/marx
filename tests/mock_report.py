# Python 3.10.11
# Creado: 13/08/2024
"""Test de reportes"""
import os
import sys

MARX_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__) + "/marx"))
sys.path.append(os.path.dirname(MARX_DIR))


from datetime import datetime
from pathlib import Path

from marx import Marx
from marx.automation import LoansHandler
from marx.reporting import Report
from marx.reporting.tools import TreeTable, formulas

TESTING_DB = Path(__file__).parent / "data" / "Ago_16_2024_ExpensoDB"


class MockReport(Report):
    name = "MockReport"
    title = "Mock Report"
    descripton = "Mock report for testing purposes"

    def build(self, dates: list[datetime]) -> None:
        """Balance contable

        [L0] Activos
        [L1]    Activos corrientes
        [L2]        Caja
        [L3]            Ingresos / Básicos / Personales / ...
        [L2]        Ahorro
        [L3]            Hucha / Reserva
        [L1]    Activos financieros
        [L2]        <categoría>
        [L3]            <concepto>

        """
        self.table = TreeTable("Balance", headers=[dt.strftime("%d/%m/%Y") for dt in dates])

        # esqueleto de la tabla
        self.table.append("A", "Activos", omit_if_childless=False)
        self.table["A"].append("AC", "Activos corrientes", omit_if_childless=False)
        self.table["AC"].append("ACC", "Caja", omit_if_childless=True)
        self.table["AC"].append("ACA", "Ahorro", omit_if_childless=True)
        self.table["AC"].append("ACB", "Cuentas a cobrar", omit_if_childless=True)
        self.table["A"].append("AF", "Activos financieros", omit_if_childless=False)
        self.table.append("P", "Pasivos", omit_if_childless=False)
        self.table["P"].append("PD", "Deudas", omit_if_childless=False)
        self.table["PD"].append("PDS", "Deudas a corto plazo", omit_if_childless=True)
        self.table["PD"].append("PDL", "Deudas a largo plazo", omit_if_childless=True)
        # TODO: mecanismo para distinguir entre deudas a corto y largo plazo
        self.table.append("N", "Patrimonio neto", omit_if_childless=False)
        self.table.append("NC", "Capital", omit_if_childless=False)

        # por defecto, suman los valores de sus hijos
        for node in self.table.iter_all():
            node.values[...] = "=SUM(@CHILDREN)"
        # excepciones
        self.table["NC"].values[...] = "={A} - {P}"

        # caja, ahorro y activos financieros
        for event in self.data.events.subset(status=1):
            accounts = []
            if event.flow in (0, 1) and not event.dest.disabled:
                accounts.append((event.dest, 1))
            if event.flow in (0, -1) and not event.orig.disabled:
                accounts.append((event.orig, -1))
            for account, sign in accounts:
                if account.name == "Inversión":
                    node = self.table["AF"].append(
                        event.category.code,
                        event.category.title,
                        omit_if_childless=True,
                        sort_with=event.category.code,
                    )
                    node.values[...] = "=SUM(@CHILDREN)"
                    title, sort_with = event.concept, event.concept
                elif account.name in ("Hucha", "Reserva"):
                    node = self.table["ACA"]
                    title, sort_with = account.name, account.order
                else:
                    node = self.table["ACC"]
                    title, sort_with = account.name, account.order
                # añadir filas donde sea necesario
                new_id = f"{node.id}_{title.replace(' ', '_').lower()}"
                new = node.append(new_id, title, sort_with=sort_with)
                # añadir valores
                for date in dates:
                    if event.date <= date:
                        new.values[date.strftime("%d/%m/%Y")] += sign * event.amount
        # cuentas a cobrar
        loans_handler = LoansHandler(self.data)
        for date in dates:
            for loan in loans_handler.find(date):
                if loan.position == 1 and loan.status == 0:
                    header = f"{loan.events[-1].counterpart.name} ({loan.events[-1].concept})"
                    node = self.table["ACB"].append(f"ACB_{loan.tag}", header)
                    node.values[date.strftime("%d/%m/%Y")] += loan.remaining

        # construir la hoja de cálculo
        # TODO: tt.build(sheet=self.sheet)

    def __str__(self) -> str:
        return f"Report({self.name!r}, {self.title!r}, {self.descripton!r})"

    def show(self) -> str:
        print(self)
        self.table.show()


if __name__ == "__main__":
    m = Marx()
    m.load(TESTING_DB)

    report = MockReport(m.data)
    report.build(
        dates=[
            datetime(2023, 12, 1),
            datetime(2024, 1, 1),
            datetime(2024, 2, 1),
            datetime(2024, 3, 1),
        ]
    )
    report.show()
