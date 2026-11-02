"""Limpieza, resumen exploratorio y split train/test."""

from collections import Counter

import pandas as pd
from sklearn.model_selection import train_test_split

from src.config import LABELS
from src.nlp.preprocessing import normalizar, quitar_tildes, stopwords_set, tokenizar


def limpiar(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Quita comentarios sin texto y duplicados exactos. Devuelve los datos
    limpios y un reporte de lo removido, para el panel de EDA."""
    faltantes = {col: int(n) for col, n in raw.isna().sum().items() if n}
    df = raw.copy()
    df["texto"] = df["texto"].fillna("").str.strip()
    vacios = df["texto"].eq("")
    df = df[~vacios]
    duplicados = df.duplicated(subset="texto", keep="first")
    df = df[~duplicados].reset_index(drop=True)
    reporte = {
        "raw_rows": len(raw),
        "missing_values": faltantes,
        "empty_texts_removed": int(vacios.sum()),
        "duplicates_removed": int(duplicados.sum()),
        "clean_rows": len(df),
    }
    return df, reporte


def describir(df: pd.DataFrame, keep_words: tuple, extra_stopwords: tuple,
              top_n: int = 12) -> dict:
    """Distribución de clases, longitud de los comentarios y palabras más
    frecuentes por clase."""
    palabras = df["texto"].str.split().str.len()
    stop = stopwords_set("adjusted", keep_words, extra_stopwords)
    top_palabras = {}
    for clase in LABELS:
        counter = Counter()
        for texto in df.loc[df["clase"] == clase, "texto"]:
            counter.update(t for t in tokenizar(normalizar(texto))
                           if quitar_tildes(t) not in stop)
        top_palabras[clase] = counter.most_common(top_n)

    return {
        "class_counts": df["clase"].value_counts().reindex(LABELS).to_dict(),
        "length_words": {
            clase: {
                "mean": round(float(palabras[df["clase"] == clase].mean() or 0), 1),
                "median": float(palabras[df["clase"] == clase].median() or 0),
                "max": int(palabras[df["clase"] == clase].max() or 0),
            } for clase in LABELS
        },
        "length_histogram": _histograma(palabras),
        "top_words": top_palabras,
        "origin_counts": df["origen"].value_counts().to_dict(),
        "style_by_label": pd.crosstab(df["clase"], df["estilo"])
                            .reindex(LABELS).fillna(0).astype(int).to_dict(orient="index"),
    }


def _histograma(valores: pd.Series, ancho: int = 3) -> list[dict]:
    """Agrupa longitudes en bins de `ancho` palabras."""
    bins = (valores // ancho) * ancho
    counts = bins.value_counts().sort_index()
    return [{"from": int(b), "to": int(b + ancho - 1), "count": int(c)}
            for b, c in counts.items()]


def split(df: pd.DataFrame, test_size: float, seed: int):
    """Split estratificado con semilla fija: mismas proporciones de cada clase
    en train y test, y el mismo split cada vez."""
    return train_test_split(df, test_size=test_size, stratify=df["clase"],
                            random_state=seed)
