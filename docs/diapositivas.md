# Diapositivas de la presentación — ComentaVenta IA

> 10 diapositivas, ~10 minutos de exposición grupal. Cada slide tiene título, bullets a decir y una nota de qué mostrar en pantalla.

---

## 1 — Portada

**ComentaVenta IA**
*Clasificador en tiempo real de comentarios de TikTok Live*

- Materia: Tópicos y Programación Avanzada
- Integrantes: JOVAS45 · Black7in
- Noviembre 2026

> **En pantalla:** logo o captura del panel Live con comentarios clasificados.

---

## 2 — El problema

En un live de venta entran decenas de comentarios por minuto. El vendedor:

- Pierde pedidos ("yo el 3", "mío 50") porque no alcanza a leerlos.
- Deja preguntas sin responder y el espectador se va.
- No nota cuando se repite la misma objeción ("¿es original?", "muy caro").
- Al terminar no sabe qué pasó en su live.

> **En pantalla:** captura real de un chat de live boliviano cualquiera.

---

## 3 — Qué hacemos

Clasificamos cada comentario del chat en **5 clases accionables**:

| Clase | Acción del vendedor |
|---|---|
| 🛒 Pedido | Anotarlo o separar |
| ❓ Pregunta | Responder en cámara |
| 🚚 Pago y envío | Explicar pago / entrega |
| ⚠️ Objeción | Dar confianza |
| 💬 Otros | Ignorar |

Priorizamos **F1 macro** porque el dataset es intencionalmente desbalanceado.

---

## 4 — Dataset (3 fuentes)

| Fuente | N | Método |
|---|---|---|
| Semillas | 100 | Escritas a mano (20 por clase) |
| GPT-4o-mini | 2 334 | Variantes generadas desde las semillas |
| TikTok Live | 172 | Capturados con la librería `TikTokLive` y auto-etiquetados |
| **Total** | **2 607** | |

Dataset documentado, reproducible con semilla fija 42.

> **En pantalla:** gráfico de distribución del notebook `01_eda.ipynb`.

---

## 5 — Pipeline NLP

Un solo `TextPreprocessor` (sklearn transformer) para entrenamiento y producción:

1. **Normalizar** — minúsculas, URLs, emojis → palabras, `yooo`→`yo`, `xfa`→`porfa`
2. **Tokenizar**
3. **Stop words ajustadas** — preservamos `yo`, `mío`, `no`, `caro`, `bs`...
4. **Stemming** Snowball español (ganó a lematización por 0.6 pts F1 CV)
5. **Quitar tildes**

> **En pantalla:** la sección "¿Cómo lo entendió el sistema?" del frontend mostrando los 7 pasos sobre "yooo quiero el NEGRO!! xfa 😍".

---

## 6 — Modelos y resultados

| Modelo | CV F1 macro | Test F1 macro | Test accuracy |
|---|---|---|---|
| 🥇 **Naive Bayes** (producción) | **0.876** | **0.880** | **89.5%** |
| Regresión logística | 0.874 | 0.870 | 89.3% |
| Línea base | 0.126 | 0.126 | 46.0% |

Grilla con `GridSearchCV` 5-fold sobre ~80 configuraciones. Baseline aporta la referencia obligatoria del enunciado.

> **En pantalla:** la pantalla **Panel del modelo** del frontend.

---

## 7 — Matriz de confusión y errores

- **Pedido** se detecta casi perfecto (F1 0.931).
- **Pregunta** confunde a veces con Objeción ("está caro?") y Otros.
- **Objeción** confunde con Otros (comentarios con tono negativo sin crítica directa).

> **En pantalla:** matriz de confusión y top-palabras influyentes por clase.

---

## 8 — Arquitectura

4 servicios en Docker Compose: `db`, `trainer` (corre una vez), `api`, `frontend`.

- **Backend:** FastAPI con endpoints HTTP + WebSocket.
- **Frontend:** React + Vite + nginx, 6 pantallas.
- **BD:** PostgreSQL (dataset, entrenamientos, predicciones, sesiones de live).

Clave: el `Pipeline` se serializa completo (`TextPreprocessor` + `TfidfVectorizer` + modelo). La API nunca reimplementa preprocesamiento.

---

## 9 — Demo en vivo

1. **Analizar texto** — "mío el 3 porfa" → Pedido 98%, mostrar "cómo lo entendió"
2. **Carga de archivo** — subir CSV con 12 comentarios → tabla y resumen
3. **Panel del modelo** — comparación, F1 por clase, matriz de confusión
4. **Datos** — distribución y 3 orígenes
5. **Live** — conectarnos a un @usuario que esté transmitiendo

---

## 10 — Cierre

- Dataset propio, reproducible, con 3 fuentes complementarias.
- Pipeline NLP completo con los 5 pasos exigidos.
- Dos modelos + línea base, elegidos por validación cruzada.
- Backend REST + WebSocket, Frontend con 6 pantallas, todo en Docker.
- Repo en GitHub con commits distribuidos entre los 2 integrantes.

**¿Preguntas?**

> **En pantalla:** URL del repo y de Swagger (`/api/docs`).
