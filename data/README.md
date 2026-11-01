# Datos — ComentaVenta IA

## Estructura

```
data/
├── raw/
│   ├── comentarios.csv       # dataset crudo (sintético) — versionado
│   ├── semillas.json         # comentarios "madre" escritos a mano (versionado)
│   ├── test_manual.csv       # test set 100% escrito a mano (versionado)
│   └── demo_live.jsonl       # live grabado para modo demostración (versionado)
├── processed/                # datos transformados por el pipeline — NO versionados
└── README.md                 # este archivo
```

## Diccionario de datos (`comentarios.csv`)

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | int | Identificador único |
| `texto` | str | Comentario tal como aparecería en el chat del live |
| `clase` | str | Una de: `Pedido`, `Pregunta`, `PagoEnvio`, `Objecion`, `Otros` |
| `producto` | str | Tipo de producto al que alude (ropa, calzado, maquillaje, accesorios, tecnologia). Puede estar vacío. |
| `estilo` | str | Forma de escribir dominante: `normal`, `abreviaturas`, `emojis`, `mayusculas`, `letras_repetidas`, `mixto` |
| `origen` | str | `sintetico` (generado por script), `manual` (escrito a mano para test), `live-real` (capturado de un live real, si aplica) |

## Diccionario de datos (`demo_live.jsonl`)

Un JSON por línea, cada línea = un comentario reproducible por el modo demostración.

```json
{"segundos_desde_inicio": 12.3, "usuario": "vecinaCotoca", "texto": "cuanto sale el negro?"}
```

Los `segundos_desde_inicio` se usan para reproducir el live a su ritmo original (el worker duerme la diferencia entre uno y el siguiente).

## Origen y licencia

- **Origen:** dataset **sintético** generado por un script Python a partir de ~100 comentarios "semilla" escritos a mano, expandidos con GPT-4o-mini.
- **Herramienta:** OpenAI API, modelo `gpt-4o-mini`.
- **Fecha de obtención:** _(se completa al generar)_
- **Semilla aleatoria:** 42 (ver `params.yaml`).
- **Licencia:** uso académico. No contiene datos personales reales ni comentarios capturados de usuarios reales de TikTok.
- **Limitaciones:** por ser sintético, puede subestimar la variedad real de comentarios y sobrestimar la facilidad del problema. El test set manual intenta compensar eso con casos más "del mundo real".
