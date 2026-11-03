# API — ComentaVenta IA

Backend FastAPI con documentación interactiva autogenerada.

## Base URLs

| Ambiente | URL |
|---|---|
| Docker Compose | `http://localhost:8000` |
| Swagger (docs interactivas) | `http://localhost:8000/api/docs` |
| OpenAPI JSON | `http://localhost:8000/api/openapi.json` |

Todas las respuestas y los mensajes de error están en **español**. El cuerpo de los errores tiene la forma:

```json
{ "error": "mensaje principal", "detalles": [{"campo": "...", "mensaje": "..."}] }
```

## Endpoints

### `GET /api/health`

Estado del servicio. Útil para healthchecks de Docker.

```bash
curl http://localhost:8000/api/health
```

```json
{
  "estado": "ok",
  "modelo_cargado": true,
  "modelo": "Naive Bayes multinomial",
  "version": "20261103-042035",
  "base_de_datos": "conectada"
}
```

### `POST /api/predict`

Clasifica **un** comentario. Devuelve clase, probabilidades y los pasos del preprocesamiento.

Validaciones:
- `texto` obligatorio, string.
- No vacío (tras `strip`).
- ≤ 300 caracteres.
- Debe contener al menos una letra.

```bash
curl -X POST http://localhost:8000/api/predict \
     -H "Content-Type: application/json" \
     -d '{"texto":"mio el 3 porfa"}'
```

```json
{
  "clase": "Pedido",
  "probabilidad": 0.9813,
  "probabilidades": {
    "Pedido": 0.9813, "Pregunta": 0.0048, "PagoEnvio": 0.0036,
    "Objecion": 0.0006, "Otros": 0.0097
  },
  "preprocesamiento": {
    "original": "mio el 3 porfa",
    "normalizado": "mio el porfa",
    "tokens": ["mio", "el", "porfa"],
    "stopwords_eliminadas": ["el"],
    "sin_stopwords": ["mio", "porfa"],
    "raices": ["mio", "porf"],
    "final": ["mio", "porf"],
    "metodo": "stem"
  },
  "modelo": {"nombre": "Naive Bayes multinomial", "version": "20261103-042035"},
  "tiempo_ms": 1.6
}
```

### `POST /api/predict/batch`

Clasifica varios comentarios de un archivo subido. Acepta:
- **`.csv`** con una columna llamada `texto`.
- **`.txt`** con un comentario por línea.

Límites: 500 filas, 1 MB. Las filas inválidas se omiten y se informan.

```bash
curl -X POST http://localhost:8000/api/predict/batch \
     -F "archivo=@frontend/public/ejemplo_batch.csv"
```

### `GET /api/metrics`

Devuelve el `metrics.json` que generó el entrenamiento: comparación de modelos, matriz de confusión, F1 por clase, palabras influyentes, análisis de errores por estilo. Es lo que consume la pantalla **Panel del modelo**.

### `GET /api/history?limit=20`

Últimas predicciones guardadas en PostgreSQL (origen: individual, lote, live).

### `GET /api/trainings`

Historial de corridas de entrenamiento registradas en la tabla `entrenamientos`.

### `WebSocket /api/live/{usuario}`

Stream de comentarios clasificados desde un live activo de TikTok.

Mensajes emitidos por el servidor:

```json
{"tipo": "conectado",    "usuario": "@xxx"}
{"tipo": "comentario",   "texto": "...", "autor": "nick",
                         "clase": "Pedido", "probabilidad": 0.92,
                         "probabilidades": {...},
                         "recibido_en": "2026-11-03T14:00:00Z"}
{"tipo": "desconectado", "razon": "fin del live"}
{"tipo": "error",        "mensaje": "..."}
```

Mensaje aceptado del cliente:
```json
{"accion": "detener"}
```

## Códigos de error

| Código | Significado |
|---|---|
| `422` | Entrada inválida (texto vacío, muy largo, formato no soportado...) |
| `413` | Archivo supera el límite de 1 MB |
| `503` | Modelo no cargado o base de datos no disponible |
