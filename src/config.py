"""Rutas y parámetros compartidos entre los módulos de datos, entrenamiento y API."""

import os
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
PARAMS_PATH = Path(os.getenv("PARAMS_PATH", ROOT / "params.yaml"))
ARTIFACTS_DIR = Path(os.getenv("ARTIFACTS_DIR", ROOT / "artifacts"))

MODEL_PATH = ARTIFACTS_DIR / "model.joblib"
METRICS_PATH = ARTIFACTS_DIR / "metrics.json"
EXPERIMENTS_PATH = ARTIFACTS_DIR / "experiments.csv"
ERRORS_PATH = ARTIFACTS_DIR / "errors.csv"
INFLUENTIAL_WORDS_PATH = ARTIFACTS_DIR / "influential_words.json"

# Las 5 clases de ComentaVenta IA. El orden define la prioridad de desempate
# para comentarios ambiguos: Pedido > Objeción > Pago y envío > Pregunta > Otros.
LABELS = ["Pedido", "Objecion", "PagoEnvio", "Pregunta", "Otros"]

LABEL_DISPLAY = {
    "Pedido": "Pedido",
    "Objecion": "Objeción",
    "PagoEnvio": "Pago y envío",
    "Pregunta": "Pregunta",
    "Otros": "Otros",
}


@lru_cache
def load_params() -> dict:
    """Lee params.yaml una sola vez y lo cachea en memoria."""
    with open(PARAMS_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def database_url() -> str | None:
    """None significa 'correr sin base de datos' (tests, notebook)."""
    return os.getenv("DATABASE_URL") or None
