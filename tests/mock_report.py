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

TESTING_DB = Path(__file__).parent / "data" / "Ago_10_2024_ExpensoDB"


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
        tt = TreeTable("Balance")
        tt.set_headers([dt.strftime("%d/%m/%Y") for dt in dates])

        # esqueleto de la tabla
        tt.append("A", "Activos", omit_if_childless=False)
        tt["A"].append("AC", "Activos corrientes", omit_if_childless=False)
        tt["AC"].append("ACC", "Caja", omit_if_childless=True)
        tt["AC"].append("ACA", "Ahorro", omit_if_childless=True)
        tt["AC"].append("ACB", "Cuentas a cobrar", omit_if_childless=True)
        tt["A"].append("AF", "Activos financieros", omit_if_childless=False)
        tt.append("P", "Pasivos", omit_if_childless=False)
        tt["P"].append("PD", "Deudas", omit_if_childless=False)
        tt["PD"].append("PDS", "Deudas a corto plazo", omit_if_childless=True)
        tt["PD"].append("PDL", "Deudas a largo plazo", omit_if_childless=True)
        # TODO: mecanismo para distinguir entre deudas a corto y largo plazo
        tt.append("N", "Patrimonio neto", omit_if_childless=False)
        tt.append("NC", "Capital", omit_if_childless=False)

        # por defecto, suman los valores de sus hijos
        for node in tt.iter_all():
            node.values[...] = formulas.SUM_CHILDREN
        # excepciones
        tt["NC"].values[...] = formulas.new("{A} - {P}")

        # caja, ahorro y activos financieros
        for event in self.data.events.subset(status=1):
            accounts = []
            if event.flow in (0, 1) and not event.dest.disabled:
                accounts.append((event.dest, 1))
            if event.flow in (0, -1) and not event.orig.disabled:
                accounts.append((event.orig, -1))
            for account, sign in accounts:
                if account.name == "Inversión":
                    node = tt["AF"].append(
                        event.category.code,
                        event.category.title,
                        omit_if_childless=True,
                        sort_with=event.category.code,
                    )
                    title, sort_with = event.concept, event.concept
                elif account.name in ("Hucha", "Reserva"):
                    node = tt["ACA"]
                    title, sort_with = account.name, account.order
                else:
                    node = tt["ACC"]
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
                if loan.position != 1 or loan.status != 1:
                    continue
                header = f"{loan.events[-1].counterpart.name} ({loan.events[-1].concept})"
                node = tt["ACB"].append(header, id=f"ACB_{loan.tag}")
                node.values[date.strftime("%d/%m/%Y")] += loan.remaining

        # construir la hoja de cálculo
        # TODO: tt.build(sheet=self.sheet)

        print(">>>", tt)
        self.table = tt

    def __str__(self) -> str:
        s = [self.title, self.descripton, ""]
        s += [self.table.title]
        for node in self.table.iter_all():
            s += [f"|{'-'*node.level}{node!s}"]
        s += ["\\\n"]
        return "\n".join(s)


if __name__ == "__main__":
    m = Marx()
    m.load(TESTING_DB)

    report = MockReport(m.data)
    report.build(dates=[datetime(2024, 1, 1), datetime(2024, 2, 1)])
    print(report)
