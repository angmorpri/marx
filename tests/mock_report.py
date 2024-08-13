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
from marx.models import Counterpart
from marx.reporting import Report

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
        dates = {f"{date:%Y-%m-%d}": date for date in dates}
        tt = TreeTable(headers=dates.keys())
        
        # esqueleto de la tabla
        tt.append("Activos", id="A", omit_if_childless=False)
        tt["A"].append("Activos corrientes", id="AC", omit_if_childless=False)
        tt["AC"].append("Caja", id="ACC", omit_if_childless=True)
        tt["AC"].append("Ahorro", id="ACA", omit_if_childless=True)
        tt["AC"].append("Cuentas a cobrar", id="ACB", omit_if_childless=True)
        tt["A"].append("Activos financieros", id="AF", omit_if_childless=False)
        tt.append("Pasivos", id="P", omit_if_childless=False)
        tt["P"].append("Deudas", id="PD", omit_if_childless=False)
        tt["PD"].append("Deudas a corto plazo", id="PDS", omit_if_childless=True)
        tt["PD"].append("Deudas a largo plazo", id="PDL", omit_if_childless=True)
        tt.append("Patrimonio neto", id="N", omit_if_childless=False)
        tt.append("Capital", id="NC", omit_if_childless=False)
        
        # por defecto, suman los valores de sus hijos
        for node in tt.iter_all():
            node.set_values(_all_=formulas.SUM_CHILDREN)
        tt["NC"].set_values(_all_=formulas.new("{A} - {P}"))
        
        # rellenar con los datos
        for event in self.data.events.subset(status=1):
            for account, sign in ((event.orig, -1), (event.dest, 1)):
                if isinstance(account, Counterpart) or account.disabled:
                    continue
                if account.name == "Inversión":
                    node = tt["AF"].append(event.category.title, id=event.category.code, sorting_value=event.category_code, omit_if_childless=True)
                    title, sorting_value = event.concept, event.concept
                elif account.name in ("Hucha", "Reserva"):
                    node = tt["ACA"]
                    title, sorting_value = "Ahorro", 2
                else:
                    node = tt["ACC"]
                    title, sorting_value = "Caja", 1
                # añadir filas donde sea necesario
                new = node.append(title, sorting_value=sorting_value)
                # añadir valores
                for key, date in dates.items():
                    if event.date <= date:
                        new.set_values(**{key: sign * event.amount})
                
        
        
        
        table = TableBuilder()
        timetables = {f"{date:%Y-%m-%d}": date for date in sorted(dates)}
        table.set_headers(timetables)

        # Activos
 
                for date_key, date in timetables.items():
                    if event.date <= date:
                        l3_row.values[date_key] += sign * event.amount

        # Cuentas a cobrar (dentro de Activos/Activos corrientes)
        loans_handler = LoansHandler(self.data)
        for date_key, date in timetables.items():
            for loan in loans_handler.find(date):
                if loan.position != 1 or loan.status != 1:
                    continue
                loan_row = cor.append("Cuentas a cobrar", value=f.SUM_CHILDREN, sorting_key=3)
                header = f"{loan.events[-1].counterpart.name} ({loan.events[-1].concept})"
                loan_row.append(header, value={})
                loan_row.values[date_key] += loan.remaining

        # Pasivos
        table.append("Pasivos", value=f.SUM_CHILDREN)
        debts = table["Pasivos"].append("Deudas", value=f.SUM_CHILDREN)
        # TODO: mecanismo para distinguir entre deudas a corto y largo plazo

        # Patrimonio neto
        pn = table.append("Patrimonio neto", value=f.SUM_CHILDREN)
        result = pn.append("Capital", value={})
        for date_key, date in timetables.items():
            result.values[date_key] = (
                table["Activos"].values[date_key] - table["Pasivos"].values[date_key]
            )

        # Construir la Excel
        table.build(sheet=self.sheet)


if __name__ == "__main__":
    m = Marx()
    m.load(TESTING_DB)

    report = MockReport(m.data)
    print(report)
