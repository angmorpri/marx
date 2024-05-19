# Python 3.10.11
# Creado: 25/03/2024
"""API REST para Marx.

Proporciona una interfaz REST para interactuar con Marx.

Implementa la API de Marx, transformando las respuestas a un formato JSON.

Basada en FastAPI.

"""
from datetime import datetime, date as Date
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI

from marx import MarxAPI

PORT = 55055


def JSON(obj: Any):
    """Convierte un objeto a JSON."""
    if isinstance(obj, str):
        return obj
    else:
        return obj.to_json()


app = FastAPI()
app.marx = MarxAPI()


@app.get("/")
def read_root():
    return {"output": "Bienvenido a Marx!"}


# General
@app.get("/source")
def source():
    """Devuelve la fuente de datos de Marx."""
    return {"output": app.marx.current_source}


@app.get("/update-source")
def update_source():
    """Actualiza la fuente de datos de Marx."""
    new = app.marx.update_source()
    return {"output": f"{new!s}"}


@app.get("/save")
def save():
    """Guarda los cambios en la base de datos."""
    new = app.marx.save()
    return {"output": f"OK"}


# Automatización
@app.get("/autoquotas")
def autoquotas(date: Date | None = None, cfg: str | None = None):
    """Distribución de las cuotas mensuales."""
    # Argumentos
    date = datetime.now() if date is None else datetime.combine(date, datetime.min.time())
    cfg = None if cfg is None else Path(cfg)

    # Procesamiento
    try:
        distr = app.marx.autoquotas(date, cfg)
    except ValueError as err:
        return {"error": f"{err}"}
    else:
        return {
            "date": date,
            "source": {
                "amount": round(distr.source.amount, 2),
                "ratio": distr.source.ratio,
                "target": JSON(distr.source.target),
                "target_type": "payer" if isinstance(distr.source.target, str) else "account",
            },
            "sinks": [
                {
                    "amount": round(sink.amount, 2),
                    "ratio": sink.ratio,
                    "target": JSON(sink.target),
                    "target_type": "payee" if isinstance(sink.target, str) else "account",
                }
                for sink in distr.sinks
            ],
            "events": [JSON(event) for event in distr.events],
        }


@app.get("/autoinvest")
def autoinvest(date: Date | None = None, cfg: str | None = None):
    """Distribución de las inversiones mensuales."""
    # Argumentos
    date = datetime.now() if date is None else datetime.combine(date, datetime.min.time())
    cfg = None if cfg is None else Path(cfg)

    # Procesamiento
    try:
        distr = app.marx.autoinvest(date, cfg)
    except ValueError as err:
        return {"error": f"{err}"}
    else:
        return {
            "date": date,
            "source": {
                "amount": round(distr.source.amount, 2),
                "ratio": round(distr.source.ratio, 2),
                "target": JSON(distr.source.target),
                "target_type": "payer" if isinstance(distr.source.target, str) else "account",
            },
            "sinks": [
                {
                    "amount": round(sink.amount, 2),
                    "ratio": round(sink.ratio, 2),
                    "target": JSON(sink.target),
                    "target_type": "payee" if isinstance(sink.target, str) else "account",
                }
                for sink in distr.sinks
            ],
            "events": [JSON(event) for event in distr.events],
        }


@app.get("/wageparser")
def wageparser(target: str | None = None, date: Date | None = None, cfg: str | None = None):
    """Extrae los datos de un recibo de sueldo."""
    # Argumentos
    date = datetime.now() if date is None else datetime.combine(date, datetime.min.time())
    cfg = None if cfg is None else Path(cfg)

    # Procesamiento
    try:
        path, events = app.marx.wageparser(target, date, cfg)
    except ValueError as err:
        return {"error": f"{err}"}
    else:
        return {
            "path": path,
            "events": [JSON(event) for event in events],
        }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=PORT)
