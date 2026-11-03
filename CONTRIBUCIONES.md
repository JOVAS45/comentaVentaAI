# Contribuciones — ComentaVenta IA

Aporte de cada integrante al proyecto. Cada fila corresponde con el historial real de commits de esa persona (verificable con `git shortlog -sn`).

| Integrante | Rol | Aporte principal | Commits clave | Aporte en NLP o ML |
|---|---|---|---|---|
| **JOVAS45** | Infraestructura + Modelado + Frontend | Setup del proyecto (Docker, params.yaml, estructura), entrenamiento con validación cruzada y comparación de modelos, interfaz React con las 6 pantallas | `chore: configuración inicial del proyecto ComentaVenta IA`, `feat(models): entrenamiento con grilla CV, 2 modelos y baseline`, `feat(frontend): interfaz React con 6 pantallas y panel live en tiempo real` | Grilla de experimentos (3 modelos × 2 normalizadores × 2 listas de stop words × 2 n-gramas), métricas y matriz de confusión del Panel del modelo |
| **Black7in** | Datos + NLP + Backend | Dataset de 3 fuentes (semillas + GPT-4o-mini + TikTok Live), pipeline NLP (`TextPreprocessor` con los 5 pasos), backend FastAPI con HTTP y WebSocket | `feat(data): generar dataset de 2607 comentarios de 3 fuentes`, `feat(nlp): agregar TextPreprocessor con los 5 pasos del pipeline`, `feat(api): backend FastAPI con endpoints HTTP y WebSocket` | Clase `TextPreprocessor` serializable (normalización + tokenización + stop words ajustadas + stem/lemma), scraping real de TikTok Live con auto-etiquetado por LLM |

## Reglas que este archivo cumple

- Cada integrante tiene **al menos un commit significativo en NLP o ML** (última columna). Ambos pueden explicar y defender la parte NLP+ML del proyecto.
- Cada commit se hizo con la cuenta y correo del integrante correspondiente, sin cuentas compartidas.
- Mensajes de commit en formato Conventional Commits (`chore`, `feat(nlp)`, `feat(api)`, etc.) y en español.

## Cómo verificarlo

```bash
git shortlog -sne --no-merges        # commits por persona
git log --author="JOVAS45"           # commits de JOVAS45
git log --author="Black7in" --stat   # qué archivos tocó Black7in
```
