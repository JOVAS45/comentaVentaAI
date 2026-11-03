# Informe técnico — ComentaVenta IA

## 1. Problema

ComentaVenta IA es una aplicación para vendedores que transmiten por TikTok Live. Clasifica cada comentario del chat en una de **5 clases accionables** para que el vendedor pueda atender a tiempo pedidos y preguntas, y no perder ventas por el volumen del chat.

| Clase | Acción del vendedor | Ejemplos |
|---|---|---|
| **Pedido** | Anotar o separar el producto | "yo", "mío 50", "me lo separas" |
| **Pregunta** | Responder en cámara | "cuánto?", "hay en M?", "es cuero?" |
| **Pago y envío** | Explicar pago y entrega | "aceptan Tigo Money?", "envían a Montero?" |
| **Objeción** | Dar confianza o justificar precio | "muy caro", "es original?" |
| **Otros** | Ignorar | "hola desde Cotoca", "🔥", "sígueme" |

Prioridad de desempate para comentarios ambiguos: **Pedido > Objeción > Pago y envío > Pregunta > Otros**.

Especificación de producto completa: `../documentos/especificacion-producto-live.md`.

## 2. Dataset

### 2.1 Origen

El dataset tiene **tres fuentes complementarias**, declaradas en la columna `origen`:

| Fuente | Comentarios | Método |
|---|---|---|
| `semilla` | 100 | Escritos a mano por el equipo (20 por clase) |
| `gpt-4o-mini` | 2 334 | Variantes generadas por GPT-4o-mini a partir de las semillas |
| `tiktok-live` | 172 | Capturados de un live real con `TikTokLive` y auto-etiquetados por LLM |
| **Total crudo** | **2 607** | |

Semilla aleatoria: **42** (en `params.yaml`). El dataset se puede regenerar exactamente con `python -m src.data.generate`.

### 2.2 Limpieza

Tras pasar por `src.data.prepare.limpiar()`:

- 2 607 filas crudas → 2 606 filas limpias.
- 0 textos vacíos.
- 1 duplicado exacto eliminado.
- Valores faltantes: 1 011 en `producto` (es intencional; muchos "Otros" no aluden a producto).

### 2.3 Distribución de clases (desbalance intencional)

Imita un live real: la mayoría son saludos y conversación casual.

| Clase | Comentarios | % |
|---|---|---|
| Otros | 1 199 | 46.0% |
| Pregunta | 530 | 20.3% |
| Pedido | 360 | 13.8% |
| Objeción | 265 | 10.2% |
| Pago y envío | 252 | 9.7% |

Por este desbalance la métrica principal es **F1 macro**, no accuracy: queremos detectar bien las clases minoritarias accionables (Pedido, Objeción), no "acertar la mayoría".

### 2.4 División train / test

`train_test_split` estratificado con semilla fija: **2 084 train** / **522 test** (80/20). El test set se usa **una sola vez**, al final, para reportar los números de la sección 4.

## 3. Pipeline de NLP

Toda la lógica vive en `src/nlp/preprocessing.py` dentro de la clase `TextPreprocessor`, que es un transformer de scikit-learn (`fit`/`transform`). El preprocesador **no aprende nada de los datos** (`fit` es no-op), por lo que puede aplicarse antes de la validación cruzada sin leakage.

Los 5 pasos en orden:

| Paso | Qué hace | Ejemplo "yooo quiero el NEGRO!! xfa 😍" |
|---|---|---|
| **1. Normalizar** | Minúsculas, quita URLs, menciones, puntuación y números. Convierte emojis en palabras marcadoras (`emojiinteres`, `emojimolestia`, `emojialegria`, `emojidinero`). Colapsa letras repetidas (`yooo` → `yo`). Expande abreviaturas (`xfa` → `porfa`, `xq` → `porque`, `qro` → `quiero`...). | `"yo quiero el negro porfa emojiinteres"` |
| **2. Tokenizar** | `split` por espacios, descarta tokens de 1 letra. | `[yo, quiero, el, negro, porfa, emojiinteres]` |
| **3. Stop words** | Lista base de spaCy en español, **ajustada**: preserva negaciones (`no`, `ni`, `nunca`) y marcadores de pedido/objeción (`yo`, `mío`, `quiero`, `muy`, `caro`, `barato`, `bs`...). | Quita: `[el]` → `[yo, quiero, negro, porfa, emojiinteres]` |
| **4. Stemming / Lematización** | Snowball (español) o spaCy. Configurable; comparado experimentalmente. | Stem: `[yo, quier, negr, porf, emojiinteres]` |
| **5. Quitar tildes** | Al final para que `cuánto` == `cuanto`. Conserva `ñ`. | Igual (no tenía tildes) |

### 3.1 Decisiones justificadas por experimento

| Decisión | Mejor valor | F1 macro CV |
|---|---|---|
| Normalizer | **stem** (vs lemma) | 0.8764 vs 0.8706 |
| Stopword list | **adjusted** (vs spacy_full) | 0.8764 vs 0.8280 |
| N-grams | **1-2** (vs 1-1) | 0.8764 vs 0.8744 |
| Modelo | **naive_bayes** (vs logistic_regression) | 0.8764 vs 0.8744 |

La **lista ajustada** de stop words es la decisión más impactante: ganó **4.8 puntos de F1** sobre la lista completa de spaCy. Lo que hacía la lista completa era eliminar `no`, `yo`, `mío`, etc., que son justamente los marcadores más discriminativos.

### 3.2 TF-IDF

Vectorización tras el preprocesamiento (`sklearn.feature_extraction.text.TfidfVectorizer`):

- `max_features: 5 000`
- `min_df: 2` (ignora términos que aparecen en menos de 2 comentarios)
- `max_df: 0.90` (ignora términos presentes en más del 90% de los comentarios)
- `sublinear_tf: true` (`1 + log(tf)`, evita que palabras repetidas dominen)
- `ngram_range: (1, 2)` (unigramas + bigramas)

Vocabulario aprendido en producción: **799 términos**.

## 4. Modelos

### 4.1 Modelos comparados

Tres competidores (todos vistos en clase), todos entrenados sobre el mismo pipeline:

| Modelo | Rol | Justificación |
|---|---|---|
| **Línea base** (`DummyClassifier`) | Referencia obligatoria | Predice siempre la clase más frecuente ("Otros"). Demuestra cuánto aportan los modelos de verdad. |
| **Naive Bayes multinomial** | Candidato 1 | Clásico para clasificación de texto, muy rápido, interpretable vía `log_prob` por término. |
| **Regresión logística** | Candidato 2 | Buenísima con textos cortos + TF-IDF, da probabilidades calibradas y pesos interpretables por palabra. |

### 4.2 Validación cruzada y búsqueda de hiperparámetros

`GridSearchCV` con `StratifiedKFold(n_splits=5, shuffle=True, random_state=42)` sobre el conjunto de train (nunca sobre test). La grilla por modelo:

```yaml
naive_bayes:
  alpha: [0.1, 0.5, 1.0]
  fit_prior: [true, false]
logistic_regression:
  C: [0.5, 1.0, 2.0, 5.0]
  class_weight: [null, balanced]
```

Multiplicado por 2 normalizadores × 2 listas de stop words × 2 rangos de n-gramas, se evalúan **~80 configuraciones** en total.

### 4.3 Resultados en test (una sola corrida, al final)

| Modelo | CV F1 macro | Test F1 macro | Test accuracy |
|---|---|---|---|
| **Naive Bayes multinomial** ⭐ **PRODUCCIÓN** | **0.876 ± 0.022** | **0.880** | **89.5%** |
| Regresión logística | 0.874 ± 0.022 | 0.870 | 89.3% |
| Línea base | 0.126 ± — | 0.126 | 46.0% |

**En producción queda Naive Bayes multinomial** con la configuración `stem + stopwords ajustadas + unigramas+bigramas + alpha=0.1 + fit_prior=True`.

Diferencia vs línea base: **+75 puntos de F1 macro** y **+43 puntos de accuracy**. Los modelos aportan valor real.

### 4.4 Rendimiento por clase (modelo en producción)

| Clase | Precision | Recall | F1 | Soporte |
|---|---|---|---|---|
| Pedido | 0.931 | 0.931 | **0.931** | 72 |
| Otros | 0.908 | 0.946 | **0.926** | 240 |
| Pago y envío | 0.870 | 0.922 | **0.895** | 51 |
| Pregunta | 0.910 | 0.764 | **0.831** | 106 |
| Objeción | 0.789 | 0.849 | **0.818** | 53 |

Las clases accionables (Pedido 0.931, Pago y envío 0.895) se detectan muy bien. Las dos más difíciles son **Pregunta** y **Objeción** porque comparten vocabulario con otras clases (ver matriz de confusión).

### 4.5 Matriz de confusión (test)

| real \\ predicho | Pedido | Objeción | Pago y envío | Pregunta | Otros |
|---|---|---|---|---|---|
| **Pedido** | **67** | 0 | 0 | 2 | 3 |
| **Objeción** | 0 | **45** | 0 | 2 | 6 |
| **Pago y envío** | 0 | 0 | **47** | 1 | 3 |
| **Pregunta** | 2 | 7 | 5 | **81** | 11 |
| **Otros** | 3 | 5 | 2 | 3 | **227** |

Los errores más comunes:
- Pregunta → Otros (11): preguntas muy genéricas tipo "¿qué tal?" se confunden con conversación casual.
- Pregunta → Objeción (7): "está muy caro?" (duda) vs "está muy caro" (queja).
- Otros → Objeción (5): comentarios con tono negativo pero sin crítica al producto.

### 4.6 Análisis de errores por estilo de escritura

El sistema guarda en `artifacts/errors.csv` los textos del test que el modelo se equivoca, agrupables por `estilo` (abreviaturas, emojis, mayúsculas, letras_repetidas, mixto, normal). La API expone esto en `/api/metrics → accuracy_by_phenomenon`.

### 4.7 Palabras más influyentes por clase

El Panel del modelo del frontend muestra las palabras con mayor `log_prob` relativo por clase. Algunos ejemplos del modelo entrenado:

- **Pedido**: `yo`, `mio`, `quier`, `talla`, `bs`, `porf`
- **Pregunta**: `cuant`, `hay`, `ser`, `tien`, `color`
- **Pago y envío**: `envi`, `delivery`, `tigo`, `money`, `montero`
- **Objeción**: `caro`, `original`, `estaf`, `barat`, `mercad`
- **Otros**: `hola`, `saludo`, `encant`, `lind`, `cotoc`

## 5. Arquitectura

```
                          ┌──────────────────────────────────┐
                          │   Browser (http://localhost:8080)│
                          └────────────────┬─────────────────┘
                                           │
                         ┌─────────────────▼─────────────────┐
                         │  frontend (React + Vite + nginx)  │
                         │  - 6 pantallas                    │
                         │  - WebSocket para Live            │
                         └─────────┬─────────────────────┬───┘
                              /api/*                  /api/live/*
                                   │                     │
                         ┌─────────▼─────────────────────▼───┐
                         │       api (FastAPI, Python)       │
                         │  - predict / batch / explain      │
                         │  - metrics / history / health     │
                         │  - WebSocket + TikTokLive worker  │
                         └──┬──────────────────────────────┬─┘
                            │                              │
                            │ carga 1 vez al arranque      │ guarda
                            ▼                              ▼
             ┌────────────────────────┐    ┌────────────────────────┐
             │  artifacts/            │    │ db (PostgreSQL)        │
             │  - model.joblib        │    │  - comentarios         │
             │  - metrics.json        │    │  - entrenamientos      │
             │  - experiments.csv     │    │  - predicciones        │
             │  - errors.csv          │    │  - live_sesiones +     │
             └──────────▲─────────────┘    │    live_comentarios    │
                        │ serializa        └────────────▲───────────┘
                        │                               │
             ┌──────────┴────────────────┐              │ carga csv
             │  trainer (Python)         │──────────────┘
             │  python -m src.pipeline   │
             │  - limpia → split → CV    │
             │  - entrena 3 modelos      │
             │  - elige mejor por F1     │
             └──────────▲────────────────┘
                        │
             ┌──────────┴────────────────┐
             │  data/raw/comentarios.csv │
             │  (sintético, 3 orígenes)  │
             └───────────────────────────┘
```

Los 4 servicios de Docker Compose (`db`, `trainer`, `api`, `frontend`) arrancan en orden con `depends_on` + healthchecks. El `trainer` corre una vez y termina; la `api` arranca sólo si el trainer terminó OK.

### 5.1 Cómo viaja una predicción

1. Usuario escribe en Analizar; React llama a `api.predecir(texto)` → `POST /api/predict`.
2. nginx (puerto 8080) proxya al contenedor `api` (puerto 8000).
3. FastAPI valida con `PredictRequest`: no vacío, ≤ 300 caracteres, contiene letras. Si falla, responde **422** con mensaje en español.
4. `ModelService.predict()` llama a `pipeline.predict_proba(texto)`. El `Pipeline` serializado ejecuta en orden: `TextPreprocessor` → `TfidfVectorizer` → `MultinomialNB`.
5. `ModelService.explain()` pasa el texto por el **mismo** `TextPreprocessor` para devolver los pasos intermedios.
6. La predicción se guarda en `predicciones`. Si la BD falla, igual se responde.
7. React muestra la clase, probabilidades y los pasos del preprocesamiento.

El backend **nunca reimplementa preprocesamiento**: todo lo hace el primer paso del `Pipeline` guardado.

### 5.2 Integración con TikTok Live

El endpoint `WS /api/live/{usuario}` levanta un `LiveWorker` que:
1. Se conecta al chat del live con `TikTokLive`.
2. Por cada comentario que llega, lo clasifica con el mismo pipeline en milisegundos.
3. Lo empuja al WebSocket del frontend como JSON `{tipo: "comentario", clase, probabilidad, autor, texto}`.
4. Lo persiste en `live_comentarios`.

El frontend abre el WS, mantiene contadores reactivos por clase, filtros, feed y una columna de Pedidos destacada. Alertas por volumen cuando se repite mucho una clase accionable en el último minuto.

## 6. Decisiones y trade-offs

| Decisión | Alternativa descartada | Por qué |
|---|---|---|
| Dataset sintético | Scraping masivo de lives reales | TikTok no permite scraping; y la columna `tiktok-live` (172 comentarios) ya aporta variedad real |
| F1 macro como métrica principal | Accuracy | El dataset está intencionalmente desbalanceado (46% Otros); con accuracy, el baseline parecería "razonable" |
| Stemming (Snowball) | Lematización (spaCy) | Mejor F1 CV (0.8764 vs 0.8706) y mucho más rápido en runtime; spaCy lemmatiser carga 50 MB de modelo |
| Lista de stop words ajustada | Lista completa de spaCy | +4.8 puntos de F1; preservar negaciones y marcadores es crítico para esta tarea |
| Naive Bayes a producción | Regresión logística | Diferencia marginal (0.880 vs 0.870 en test); NB es más rápido y da probabilidades útiles para el umbral de confianza del 50% |
| WebSocket real a TikTok | Modo demo con JSONL | Para la defensa es más impactante ver el chat clasificado en vivo; backup = conectarse a otro live si el nuestro falla |
| FastAPI + React | Streamlit | Separa frontend de backend, API documentada en Swagger, más defendible como "producto de software" |

## 7. Limitaciones y trabajo futuro

- **Dataset mayoritariamente sintético.** Si bien incluye 172 comentarios reales, el grueso (2 334) proviene de GPT-4o-mini. Puede subestimar la variedad del lenguaje real.
- **TikTokLive es una librería no oficial.** Si TikTok cambia su API interna, la conexión real puede dejar de funcionar hasta que la librería se actualice.
- **El modelo clasifica un comentario a la vez.** No tiene memoria del contexto (qué producto se está mostrando en el video); por eso "la 7" se puede confundir con "¿cuánto cuesta la 7?".
- **Las clases accionables se agrupan por acción, no por tema.** Un "no les llegó mi pedido" se etiqueta como Objeción (contexto comercial) aunque en abstracto parezca otra cosa.
- **Umbral de confianza fijo (50%)**. Un trabajo futuro ajustaría este umbral por clase, favoreciendo recall en Pedido para no perder ventas.
