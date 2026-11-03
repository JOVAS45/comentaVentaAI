"""Pruebas del split train/test y limpieza del dataset."""

import pandas as pd

from src.data.prepare import limpiar, split


def _df_dummy() -> pd.DataFrame:
    return pd.DataFrame({
        "id": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        "texto": ["yo el 3", "cuanto?", "", "muy caro", "mio 50",
                  "hola", "aceptan QR?", "mio 50", "yooo", "linda"],
        "clase": ["Pedido", "Pregunta", "Otros", "Objecion", "Pedido",
                  "Otros", "PagoEnvio", "Pedido", "Pedido", "Otros"],
        "producto": ["ropa", "ropa", "", "ropa", "ropa",
                     "", "ropa", "ropa", "ropa", ""],
        "estilo": ["normal"] * 10,
        "origen": ["semilla"] * 10,
    })


def test_limpiar_quita_textos_vacios_y_duplicados():
    df = _df_dummy()
    limpio, reporte = limpiar(df)
    # fila 3 estaba vacía; fila 8 duplica a la 5
    assert reporte["empty_texts_removed"] == 1
    assert reporte["duplicates_removed"] == 1
    assert len(limpio) == 8


def test_split_es_estratificado_y_reproducible():
    df = _df_dummy()
    limpio, _ = limpiar(df)
    train1, test1 = split(limpio, test_size=0.3, seed=42)
    train2, test2 = split(limpio, test_size=0.3, seed=42)
    # Mismo split cada vez
    assert list(train1["id"]) == list(train2["id"])
    assert list(test1["id"]) == list(test2["id"])
