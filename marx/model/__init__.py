# Python 3.10.11
# Creado: 24/01/2024
"""Módulo para definición del modelo de datos.

También define los adaptadores para la base de datos.

"""
from .collection import Collection
from .models import Account, Category, Note, Event
from .adapters import RawAdapter, MarxAdapter, RawDataSuite, MarxDataSuite

Accounts = Collection[Account]
Categories = Collection[Category]
