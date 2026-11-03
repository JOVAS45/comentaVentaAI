"""Acceso a PostgreSQL. El esquema vive en db/init.sql."""

import json
import time
from functools import lru_cache

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.config import database_url

COLUMNAS_COMENTARIO = ["id", "texto", "clase", "producto", "estilo", "origen"]


@lru_cache
def get_engine() -> Engine | None:
    url = database_url()
    return create_engine(url, pool_pre_ping=True) if url else None


def is_available() -> bool:
    engine = get_engine()
    if engine is None:
        return False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def wait_for_db(timeout_seconds: int = 30, intervalo: float = 1.5) -> bool:
    """Espera a que PostgreSQL acepte conexiones. Útil al arranque, cuando el
    healthcheck de Docker ya pasó pero la primera conexión real todavía falla."""
    engine = get_engine()
    if engine is None:
        return False
    inicio = time.time()
    ultimo_error = None
    while time.time() - inicio < timeout_seconds:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:  # noqa: BLE001
            ultimo_error = e
            time.sleep(intervalo)
    print(f"[db] timeout esperando PostgreSQL ({timeout_seconds}s): {ultimo_error}")
    return False


def count_comentarios(engine: Engine) -> int:
    with engine.connect() as conn:
        return conn.execute(text("SELECT count(*) FROM comentarios")).scalar_one()


def replace_comentarios(engine: Engine, df: pd.DataFrame) -> None:
    """Carga el CSV crudo en la base, reemplazando lo que había."""
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE comentarios"))
        df[COLUMNAS_COMENTARIO].to_sql("comentarios", conn, if_exists="append", index=False)


def read_comentarios(engine: Engine) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(text("SELECT * FROM comentarios ORDER BY id"), conn)


def record_training(engine: Engine, run: dict) -> None:
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO entrenamientos (version, modelo, configuracion, cv_f1_macro,
                test_f1_macro, test_accuracy, n_entrenamiento, n_prueba)
            VALUES (:version, :modelo, CAST(:configuracion AS JSONB), :cv_f1_macro,
                :test_f1_macro, :test_accuracy, :n_entrenamiento, :n_prueba)
        """), {**run, "configuracion": json.dumps(run["configuracion"])})


def record_predictions(engine: Engine, rows: list[dict]) -> None:
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO predicciones (texto, clase, probabilidad, probabilidades,
                version_modelo, origen)
            VALUES (:texto, :clase, :probabilidad, CAST(:probabilidades AS JSONB),
                :version_modelo, :origen)
        """), [{**r, "probabilidades": json.dumps(r["probabilidades"])} for r in rows])


def recent_predictions(engine: Engine, limit: int) -> list[dict]:
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT id, fecha, texto, clase, probabilidad, version_modelo, origen
            FROM predicciones ORDER BY fecha DESC, id DESC LIMIT :limit
        """), {"limit": limit})
        return [dict(row._mapping) for row in result]


def training_history(engine: Engine) -> list[dict]:
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT version, fecha, modelo, cv_f1_macro, test_f1_macro, test_accuracy
            FROM entrenamientos ORDER BY fecha DESC
        """))
        return [dict(row._mapping) for row in result]
