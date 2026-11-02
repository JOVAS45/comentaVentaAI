# Datos — ComentaVenta IA

## Estructura

```
data/
├── raw/
│   ├── comentarios.csv       # dataset crudo (3 orígenes) — versionado
│   ├── semillas.json         # comentarios "madre" escritos a mano — versionado
│   └── comentarios_live.csv  # comentarios reales de TikTok Live (opcional) — versionado
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
| `origen` | str | Uno de tres: `semilla` (escrito a mano), `gpt-4o-mini` (variante sintética), `tiktok-live` (capturado de un live real y auto-etiquetado por LLM) |

## Origen y licencia

El dataset tiene **tres orígenes complementarios**, todos declarados en la columna `origen` de cada fila:

1. **`semilla`** — ~100 comentarios escritos a mano por el equipo. Son la base; cubren las 5 clases con ejemplos variados en producto, estilo y longitud. Ver `data/raw/semillas.json`.
2. **`gpt-4o-mini`** — variantes sintéticas generadas por el script `src/data/generate.py`, que pasa cada semilla por el modelo `gpt-4o-mini` de OpenAI pidiendo N variantes nuevas de la misma clase. Semilla aleatoria 42 (ver `params.yaml`).
3. **`tiktok-live`** — comentarios reales capturados de lives activos con el script `src/data/scrape_live.py` (usa la librería `TikTokLive`) y auto-etiquetados por `gpt-4o-mini`. Son los más "ruidosos" y realistas; se usan para complementar el sintético.

- **Herramientas:** OpenAI API (`gpt-4o-mini`), librería `TikTokLive`.
- **Fecha de obtención:** _(se completa al generar)_
- **Licencia:** uso académico. No se persisten nombres de usuario ni datos personales de quienes comentan en los lives: solo el texto. Los comentarios capturados son públicos por definición (los emite cualquiera en el chat de un live abierto).
- **Limitaciones:**
  - El origen `gpt-4o-mini` tiene sesgos propios del modelo (puede repetir patrones, usar lenguaje más formal del esperado).
  - El origen `tiktok-live` depende del tipo de live capturado (si todos son del mismo vendedor, se puede sobre-ajustar a su jerga).
  - Las etiquetas asignadas por LLM se validan por muestreo manual del equipo antes de usar.
