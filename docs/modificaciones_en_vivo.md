# Modificaciones en vivo — recetario para la defensa

Guía para los cambios chicos que el docente puede pedir durante la defensa (sección 8.4 del enunciado). Cada receta explica **dónde tocar, cómo aplicar y qué commit dejar**.

El flujo general tras cualquier cambio en código Python o `params.yaml`:

```bash
# Reentrenar
docker compose run --rm trainer python -m src.pipeline
# Reiniciar la API para que cargue el nuevo artifacts/model.joblib
docker compose restart api
```

El código de `src/`, `api/` y `params.yaml` está montado como volumen; no hace falta rebuild.

---

## NLP

### Agregar o quitar una stop word

**Archivo:** `params.yaml` → `nlp.keep_words` o `nlp.extra_stopwords`.

Ejemplo: "¿qué pasa si incluimos `mio` como stop word?"

```yaml
nlp:
  keep_words: ["no", "ni", ...]  # quitar "mio" de esta lista
  extra_stopwords: ["mio"]        # (o agregarlo acá)
```

Reentrenar y comparar: el F1 macro de **Pedido** debería caer varios puntos (observación: `mio` + `yo` son los marcadores más fuertes de Pedido).

**Commit sugerido:** `fix(nlp): revisar impacto de 'mio' en la clasificación de Pedido`.

### Cambiar el rango de n-gramas

**Archivo:** `params.yaml` → `experiments.ngram_ranges`.

```yaml
experiments:
  ngram_ranges: [[1, 1]]   # solo unigramas (vs la combinación 1-1 y 1-2 por defecto)
```

Al reentrenar, el reporte comparativo (`artifacts/experiments.csv`) muestra cómo cae el F1 CV sin bigramas.

**Commit sugerido:** `experiment(nlp): comparar unigramas vs unigramas+bigramas`.

### Cambiar stemming por lematización (y viceversa)

Para forzar lemma como único normalizador en producción:

```yaml
experiments:
  normalizers: [lemma]  # (en vez de [stem, lemma])
```

Reentrenar. En el panel del modelo se verá el F1 del nuevo "ganador" entre configuraciones solo-lemma.

Para probar en vivo un texto con los dos métodos, cambiar manualmente `src/nlp/preprocessing.py` → `TextPreprocessor(normalizer="lemma")` y comparar la salida de `/api/predict`.

**Commit:** `experiment(nlp): forzar lematización y re-evaluar`.

---

## Modelado

### Cambiar un hiperparámetro

**Archivo:** `params.yaml` → `experiments.models`.

Ejemplo: `alpha` del Naive Bayes.

```yaml
experiments:
  models:
    naive_bayes:
      alpha: [1.0, 5.0, 10.0]   # suavizado más fuerte
      fit_prior: [true]
```

Reentrenar. El `metrics.json` ahora tiene el mejor `alpha` como `production.config.hyperparameters.alpha`.

**Commit:** `experiment(models): aumentar alpha del Naive Bayes`.

### Agregar una métrica

**Archivo:** `src/models/evaluate.py` → `classification_metrics()`.

Ejemplo: agregar F1 **ponderado** además del macro.

```python
from sklearn.metrics import f1_score

return {
    "accuracy": ...,
    "f1_macro": round(float(f1_score(..., average="macro", ...)), 4),
    "f1_weighted": round(float(f1_score(..., average="weighted", labels=LABELS, zero_division=0)), 4),
    ...
}
```

Reentrenar + reiniciar API. La nueva métrica aparece en `/api/metrics` y se puede mostrar en el frontend editando `componentes/PanelModelo.jsx`.

**Commit:** `feat(evaluate): agregar F1 weighted como métrica complementaria`.

---

## Backend

### Agregar una validación nueva

**Archivo:** `api/schemas.py` → `validate_text()`.

Ejemplo: rechazar textos de menos de 2 palabras.

```python
def validate_text(value: str) -> str:
    value = value.strip()
    if not value: raise ValueError("El texto está vacío.")
    if len(value.split()) < 2:
        raise ValueError("Escribí al menos dos palabras.")
    ...
```

`docker compose restart api` (no necesita reentrenar). Probar con `curl` o desde la pantalla Analizar.

**Commit:** `feat(api): rechazar textos de menos de 2 palabras`.

### Agregar un endpoint nuevo

**Archivo:** `api/main.py`.

Ejemplo: endpoint que devuelve la cantidad de predicciones por clase guardadas en la base.

```python
@app.get("/api/stats", tags=["modelo"])
def stats():
    engine = require_database()
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT clase, count(*) AS n FROM predicciones GROUP BY clase"
        )).all()
    return {clase: int(n) for clase, n in rows}
```

Reiniciar API y verificar en `/api/docs` que aparece el nuevo endpoint.

**Commit:** `feat(api): endpoint /stats con conteo de predicciones por clase`.

---

## Frontend

### Mostrar un dato nuevo de la API

**Archivo:** `frontend/src/componentes/PanelModelo.jsx` o el que corresponda.

Ejemplo: mostrar también `cv_f1_macro_std` como barra de error en la tabla.

```jsx
<td className="mono">
  {(m.cv_f1_macro * 100).toFixed(1)}%
  <span className="chico tenue"> ±{(m.cv_f1_macro_std * 100).toFixed(1)}</span>
</td>
```

Rebuild del frontend:

```bash
docker compose up -d --build frontend
```

**Commit:** `feat(frontend): mostrar desviación estándar de CV en el panel del modelo`.

### Cambiar la paleta de colores de una clase

**Archivo:** `frontend/src/clases.js` → objeto `META`.

```js
Pedido: { ..., color: "#22d3ee", colorSuave: "#22d3ee22" },
```

Rebuild frontend. El cambio se propaga a: contadores Live, feed, badge en Analizar, barras de probabilidad, panel del modelo, matriz de confusión.

**Commit:** `style(frontend): cambiar color de Pedido a cian`.

---

## Qué NO hacer en la defensa

- **No corras `make clean`.** Borra la base y los artefactos; perdemos toda la demo.
- **No hagas `docker compose down -v`.** Lo mismo: el `-v` borra el volumen de PostgreSQL.
- **No cambies `seed` en `params.yaml`.** Los experimentos cambiarían y no quedarían reproducibles.
- **No borres `artifacts/model.joblib` sin reentrenar inmediatamente.** La API arranca "degradada" si no lo encuentra.
