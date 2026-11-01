# API

> Esqueleto. Se completa cuando los endpoints estén implementados.

## Base

- Base URL (Docker Compose): `http://localhost:8000`
- Documentación interactiva (Swagger): `http://localhost:8000/api/docs`

## Endpoints previstos

| Método | Ruta | Qué hace |
|---|---|---|
| `GET` | `/api/health` | Estado del servicio |
| `POST` | `/api/predict` | Predice sobre un texto |
| `POST` | `/api/predict-batch` | Predice sobre un CSV subido |
| `POST` | `/api/explain` | Devuelve pasos de NLP para un texto |
| `GET` | `/api/metrics` | Métricas del modelo en producción |
| `GET` | `/api/history` | Historial de predicciones |

Los contratos (`schemas.py`) y ejemplos con `curl` se agregarán cuando el backend esté implementado.
