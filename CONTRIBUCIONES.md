# Contribuciones — ComentaVenta IA

Este archivo refleja el aporte de cada integrante al proyecto. Cada fila debe corresponder con el historial real de commits de esa persona (verificable con `git shortlog -sn`).

| Integrante | Rol | Aporte principal | Commits clave | Aporte en NLP o ML |
|---|---|---|---|---|
| _(Integrante 1)_ | _(Datos y NLP + Backend)_ | _(a completar)_ | _(a completar tras los primeros commits)_ | _(a completar)_ |
| _(Integrante 2)_ | _(Modelado + Frontend)_ | _(a completar)_ | _(a completar tras los primeros commits)_ | _(a completar)_ |

## Reglas que este archivo debe cumplir

- Cada integrante tiene **al menos un commit significativo en NLP o ML**: ambos serán preguntados sobre ello (última columna).
- El trabajo en pareja se registra en el commit con una línea `Co-authored-by: Nombre <correo>`.
- Lo que no está en el historial de una persona no cuenta como trabajo suyo.

## Cómo verificarlo

```bash
git shortlog -sn --no-merges                    # commits por persona
git log --author="Nombre" --oneline             # commits de una persona
git log --author="Nombre" --stat -- src/nlp     # qué tocó en NLP
```
