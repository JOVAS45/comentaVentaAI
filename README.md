# ComentaVenta IA

> Proyecto Integrador — **Tópicos y Programación Avanzada**.

Aplicación web para vendedores que transmiten en vivo por TikTok. Clasifica cada comentario del chat en **5 clases** (Pedido, Pregunta, Pago y envío, Objeción, Otros) y presenta un panel en tiempo real: el vendedor ve de un vistazo qué comentarios son ventas, cuáles necesitan respuesta y cuáles puede ignorar.

Al terminar la transmisión entrega un reporte con las estadísticas del live.

Las cinco capas del proyecto, todas en contenedores Docker:

| Capa | Qué hace | Dónde |
|---|---|---|
| Datos | ~2.500 comentarios sintéticos etiquetados, cargados en PostgreSQL | `data/`, `db/`, `src/data/` |
| Pipeline de NLP | Normalización (incluye letras repetidas y abreviaturas), tokenización, stop words ajustadas, stemming/lematización, n-gramas, TF-IDF | `src/nlp/` |
| Modelos | Regresión logística y Naive Bayes multinomial, comparados contra línea base con CV | `src/models/` |
| Backend | API REST + WebSocket con FastAPI | `api/` |
| Frontend | React + Vite + nginx | `frontend/` |

## Levantar el sistema

### Requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows / macOS) o Docker Engine con Compose v2 (Linux).
- ~3 GB libres. La primera construcción tarda ~5 min; las siguientes, segundos.

### Pasos

```bash
git clone <url-del-repositorio>
cd proyecto
docker compose up --build
```

Espera a que el servicio `trainer` termine (unos 30-60 s) y abre:

| Qué | Dirección |
|---|---|
| Aplicación | http://localhost:8080 |
| Documentación de la API (Swagger) | http://localhost:8000/api/docs |
| PostgreSQL (DBeaver / pgAdmin) | `localhost:5433`, usuario/clave/base `proyecto` |

Para detener: `docker compose down`. La base se conserva en el volumen `pgdata`; `docker compose down -v` la borra.

### Puertos ocupados

Crea un `.env` junto al `docker-compose.yml`:

```bash
API_PORT=8001
FRONTEND_PORT=8090
DB_PORT=5434
```

## Modo demostración vs modo real

- **Modo demostración:** reproduce un live guardado (`data/raw/demo_live.jsonl`) comentario por comentario con su ritmo original. No requiere internet ni que haya alguien transmitiendo. **Es la vía recomendada para la demo del proyecto.**
- **Modo real:** se conecta a un live activo de TikTok mediante la librería `TikTokLive`. Requiere que la cuenta `@xxx` esté transmitiendo en el momento. Es una integración experimental y puede fallar si TikTok cambia su API interna o si la cuenta está en una región bloqueada.

## Uso diario

| Tarea | Comando | Atajo |
|---|---|---|
| Levantar todo en segundo plano | `docker compose up --build -d` | `make up` |
| Reentrenar tras cambiar `params.yaml` o `src/` | `docker compose run --rm trainer python -m src.pipeline` + `docker compose restart api` | `make train` |
| Recargar el CSV en PostgreSQL y reentrenar | `docker compose run --rm trainer python -m src.pipeline --reload-data` + `docker compose restart api` | `make reload-data` |
| Tests | `docker compose --profile dev run --rm --build tests` | `make test` |
| Reconstruir frontend | `docker compose up -d --build frontend` | `make frontend` |
| JupyterLab para EDA | `docker compose --profile dev up --build notebook` → http://localhost:8888 | `make notebook` |
| Navegador de la BD | `docker compose --profile tools up -d adminer` → http://localhost:8081 | |
| Logs | `docker compose logs -f api trainer` | `make logs` |

## Estructura

```text
proyecto/
├── data/
│   ├── raw/
│   │   ├── comentarios.csv       # dataset sintético
│   │   ├── semillas.json         # comentarios "madre" a mano
│   │   ├── test_manual.csv       # test set manual
│   │   └── demo_live.jsonl       # live para modo demo
│   └── README.md                 # origen y diccionario
├── db/init.sql                   # esquema PostgreSQL
├── notebooks/                    # EDA y experimentos
├── src/
│   ├── config.py
│   ├── db.py
│   ├── pipeline.py
│   ├── data/                     # generación de dataset
│   ├── nlp/                      # TextPreprocessor
│   └── models/                   # experimentos, train, evaluate
├── api/
│   ├── main.py                   # endpoints HTTP + WebSocket
│   ├── schemas.py                # contratos y validaciones
│   ├── service.py                # carga del modelo y predicción
│   └── live.py                   # worker TikTokLive + replay demo
├── frontend/                     # React + Vite, servido por nginx
├── tests/
├── artifacts/                    # generado (NO versionado)
├── docs/
├── params.yaml
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── requirements.txt
├── requirements-dev.txt
└── CONTRIBUCIONES.md
```

## Contribuciones

Ver [CONTRIBUCIONES.md](CONTRIBUCIONES.md).
