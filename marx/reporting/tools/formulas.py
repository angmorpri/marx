# Python 3.10.11
# Creado: 15/08/2024
"""Generador de fórmulas para calcular valores de tablas jerárquicas que luego
pueden ser convertidas a Excel.

"""


class Formula:
    """Fórmula para calcular valores de una tabla jerárquica"""

    def __init__(self, formula: str) -> None:
        self._formula = formula

    def __str__(self) -> str:
        return f"Formula(self._formula)"


SUM_CHILDREN = Formula("@SUM_CHILDREN")


def new(*args, **kwargs) -> Formula:
    return Formula(*args, **kwargs)
