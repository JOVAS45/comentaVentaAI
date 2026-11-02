"""Captura comentarios de un live activo de TikTok y los auto-etiqueta con GPT-4o-mini.

Permite ampliar el dataset sintético con comentarios reales, para que la
distribución final combine tres orígenes defendibles:

    - semilla       : comentarios escritos a mano por el equipo
    - gpt-4o-mini   : variantes sintéticas generadas a partir de las semillas
    - tiktok-live   : comentarios reales capturados de un live con TikTokLive
                      y clasificados por un LLM

Uso:
    # Requiere la cuenta transmitiendo EN VIVO en este momento
    export OPENAI_API_KEY=sk-...
    python -m src.data.scrape_live --usuario @vendedora --max-segundos 600

    # Guardar en archivo propio y anexar manualmente después
    python -m src.data.scrape_live --usuario @vendedora --salida data/raw/live_dia1.csv

    # Anexar al dataset principal al terminar
    python -m src.data.scrape_live --usuario @vendedora --append-a data/raw/comentarios.csv

    # Solo capturar sin etiquetar (barato, para verificar que el live llega)
    python -m src.data.scrape_live --usuario @vendedora --sin-etiquetar

Notas:
- TikTok puede rechazar la conexión si la cuenta no está en vivo, si el live
  es privado o si tu IP está bloqueada por región.
- Se escribe incrementalmente: si el script se corta, lo recolectado ya está
  en disco.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import os
import re
import signal
import sys
from datetime import datetime
from pathlib import Path

from src.config import LABELS, ROOT

SALIDA_DEFAULT = ROOT / "data" / "raw" / "comentarios_live.csv"

PROMPT_ETIQUETADO = """Eres un clasificador de comentarios de lives de SUBASTA
de TikTok en Santa Cruz de la Sierra, Bolivia. En una subasta, la vendedora
muestra productos numerados ("la 1", "la 2", "la 3"...) y los espectadores
piden el que quieren diciendo simplemente el NÚMERO o "la X".

Clasificá el comentario en EXACTAMENTE una de estas 5 clases:

- Pedido: el usuario quiere comprar o reservar un producto.
  Patrones MUY TÍPICOS DE SUBASTA CRUCEÑA:
    * SOLO UN NÚMERO ("3", "7", "13", "15")             → quiere la prenda número N = Pedido
    * "la 3", "la siete", "el 5", "la última"           → también Pedido (pide ese ítem)
    * "yo", "yo el 3", "yooo", "siii yo"                 → quiere el que se mostró
    * "mio", "mío", "mio 50", "mio en 80 bs"             → oferta de precio
    * "lo tomo", "me lo llevo", "me lo separas"          → confirma compra
    * "la 1 en talla M", "la 7 para mi"                  → pedido con detalle
- Pregunta: pide información del producto (precio, talla, color, stock, material).
    Ejemplos: "cuanto?", "a cuanto?", "hay en M?", "es cuero?",
    "la 1 por dentro tiene cierre?", "precio?"
- PagoEnvio: pregunta por formas de pago, envíos o entregas.
    Ejemplos: "aceptan QR?", "hacen envíos?", "envían a Montero?",
    "cuanto el delivery?", "dónde queda la tienda?"
- Objecion: expresa algo que frena la compra (precio alto, desconfianza,
    mala experiencia). Ejemplos: "muy caro", "es original?", "es estafa?",
    "a mi amiga no le llegó"
- Otros: sin acción comercial clara. Saludos, elogios, emojis sueltos, spam,
    conversación casual, interjecciones.
    Ejemplos: "hola desde Cotoca", "🔥", "qué linda", "sígueme", "jaja",
    "?", "." (puntuación sola o emojis solos van en Otros)

Prioridad para comentarios ambiguos (más urgente primero):
    Pedido > Objecion > PagoEnvio > Pregunta > Otros

Reglas de desempate:
- "está caro pero lo quiero" → Pedido (gana la intención de compra)
- "la 3 cuanto sale?" → Pregunta (está pidiendo precio, no comprando aún)
- "esta bonito, hacen envíos?" → PagoEnvio (la pregunta de envío es la acción)
- Un número solo o "la X" → Pedido (patrón de subasta)
- Un signo de interrogación solo "?" → Otros (sin texto no es pregunta real)

Devolvé EXCLUSIVAMENTE un JSON con esta forma, sin texto adicional:
{"clase": "Pedido|Pregunta|PagoEnvio|Objecion|Otros",
 "producto": "ropa|calzado|maquillaje|accesorios|tecnologia|" ,
 "estilo": "normal|abreviaturas|emojis|mayusculas|letras_repetidas|mixto"}

El campo "producto" puede ser vacío si el comentario no alude a ningún producto.
"""

CAMPOS = ["id", "texto", "clase", "producto", "estilo", "origen"]
ESTILOS_VALIDOS = {"normal", "abreviaturas", "emojis", "mayusculas",
                    "letras_repetidas", "mixto"}
PRODUCTOS_VALIDOS = {"ropa", "calzado", "maquillaje", "accesorios",
                     "tecnologia", ""}


# ---------- Etiquetado con GPT-4o-mini ----------

def _clasificar(cliente_openai, texto: str) -> dict:
    """Devuelve {clase, producto, estilo} para un comentario crudo."""
    import json
    respuesta = cliente_openai.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.0,
        messages=[
            {"role": "system", "content": PROMPT_ETIQUETADO},
            {"role": "user", "content": f'Comentario: "{texto}"'},
        ],
        response_format={"type": "json_object"},
    )
    datos = json.loads(respuesta.choices[0].message.content)
    clase = datos.get("clase", "Otros")
    if clase not in LABELS:
        clase = "Otros"
    estilo = datos.get("estilo", "normal")
    if estilo not in ESTILOS_VALIDOS:
        estilo = "normal"
    producto = (datos.get("producto") or "").strip().lower()
    if producto not in PRODUCTOS_VALIDOS:
        producto = ""
    return {"clase": clase, "producto": producto, "estilo": estilo}


# ---------- Escritura incremental al CSV ----------

def _preparar_csv(salida: Path) -> int:
    """Crea el CSV con header si no existe. Devuelve el próximo id a usar."""
    salida.parent.mkdir(parents=True, exist_ok=True)
    if not salida.exists():
        with open(salida, "w", encoding="utf-8", newline="") as f:
            csv.DictWriter(f, fieldnames=CAMPOS).writeheader()
        return 1
    with open(salida, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        ids = [int(r["id"]) for r in reader if r.get("id", "").isdigit()]
    return (max(ids) + 1) if ids else 1


def _anexar_fila(salida: Path, fila: dict) -> None:
    with open(salida, "a", encoding="utf-8", newline="") as f:
        csv.DictWriter(f, fieldnames=CAMPOS).writerow(fila)


# ---------- Normalización mínima ----------

def _limpiar(texto: str) -> str:
    """Quita saltos de línea y espacios múltiples. No altera emojis ni mayúsculas."""
    return re.sub(r"\s+", " ", texto).strip()


# ---------- Captura asíncrona desde TikTok ----------

async def recolectar(usuario: str, max_comentarios: int, max_segundos: int,
                     salida: Path, cliente_openai) -> int:
    """Se conecta al live y vuelca comentarios al CSV. Devuelve cuántos capturó."""
    from TikTokLive import TikTokLiveClient
    from TikTokLive.events import CommentEvent, ConnectEvent, DisconnectEvent

    siguiente_id = _preparar_csv(salida)
    conteo = 0
    vistos = set()
    stop_event = asyncio.Event()

    client = TikTokLiveClient(unique_id=usuario)

    @client.on(ConnectEvent)
    async def _on_connect(event):
        print(f"[conectado] @{usuario}  habitación={event.unique_id}")

    @client.on(DisconnectEvent)
    async def _on_disconnect(event):
        print("[desconectado] fin del live o cierre forzado")
        stop_event.set()

    @client.on(CommentEvent)
    async def _on_comment(event):
        nonlocal siguiente_id, conteo
        if stop_event.is_set():
            return
        texto = _limpiar(getattr(event, "comment", "") or "")
        if not texto:
            return
        clave = texto.lower()
        if clave in vistos:
            return
        vistos.add(clave)
        try:
            if cliente_openai is not None:
                etiqueta = _clasificar(cliente_openai, texto)
            else:
                etiqueta = {"clase": "", "producto": "", "estilo": "normal"}
        except Exception as e:
            print(f"[warn] fallo al etiquetar '{texto}': {e}")
            etiqueta = {"clase": "Otros", "producto": "", "estilo": "normal"}
        fila = {"id": siguiente_id, "texto": texto,
                "clase": etiqueta["clase"], "producto": etiqueta["producto"],
                "estilo": etiqueta["estilo"], "origen": "tiktok-live"}
        _anexar_fila(salida, fila)
        print(f"[{conteo + 1:>3}] [{etiqueta['clase']:10s}] {texto[:80]}")
        siguiente_id += 1
        conteo += 1
        if conteo >= max_comentarios:
            print(f"[limite] alcanzados {max_comentarios} comentarios")
            stop_event.set()

    # Timeout global
    async def _temporizador():
        await asyncio.sleep(max_segundos)
        if not stop_event.is_set():
            print(f"[timeout] {max_segundos}s cumplidos")
            stop_event.set()

    tarea_timer = asyncio.create_task(_temporizador())
    tarea_cliente = asyncio.create_task(client.connect())

    try:
        await stop_event.wait()
    finally:
        tarea_timer.cancel()
        try:
            await client.disconnect()
        except Exception:
            pass
        tarea_cliente.cancel()

    return conteo


# ---------- Anexado opcional al dataset principal ----------

def _anexar_a_principal(fuente: Path, destino: Path) -> int:
    """Agrega las filas de `fuente` al final de `destino`, renumerando ids."""
    if not destino.exists():
        print(f"[warn] {destino} no existe; nada que anexar")
        return 0
    with open(destino, encoding="utf-8") as f:
        existentes = list(csv.DictReader(f))
    ultimo_id = max((int(r["id"]) for r in existentes if r.get("id", "").isdigit()), default=0)
    with open(fuente, encoding="utf-8") as f:
        nuevos = list(csv.DictReader(f))
    textos_existentes = {r["texto"].lower() for r in existentes}
    agregados = 0
    with open(destino, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        for r in nuevos:
            if r["texto"].lower() in textos_existentes:
                continue
            ultimo_id += 1
            r["id"] = ultimo_id
            w.writerow(r)
            agregados += 1
    print(f"[anexado] {agregados} filas nuevas en {destino}")
    return agregados


# ---------- CLI ----------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--usuario", required=True,
                        help='cuenta a escuchar, por ejemplo "@vendedora"')
    parser.add_argument("--max-comentarios", type=int, default=200,
                        help="corta cuando llega a este número (default: 200)")
    parser.add_argument("--max-segundos", type=int, default=600,
                        help="corta a los N segundos aunque no llegue al límite (default: 600 = 10 min)")
    parser.add_argument("--salida", type=Path, default=SALIDA_DEFAULT,
                        help=f"CSV de salida (default: {SALIDA_DEFAULT})")
    parser.add_argument("--sin-etiquetar", action="store_true",
                        help="no llama a OpenAI; guarda los comentarios sin clase (barato, para probar)")
    parser.add_argument("--append-a", type=Path, default=None,
                        help="al terminar, anexa el CSV capturado al dataset principal")
    args = parser.parse_args()

    cliente_openai = None
    if not args.sin_etiquetar:
        try:
            from openai import OpenAI
        except ImportError:
            sys.exit("Falta la librería openai. `pip install openai` o usá --sin-etiquetar.")
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            sys.exit("Falta OPENAI_API_KEY en el entorno. Exportala o usá --sin-etiquetar.")
        cliente_openai = OpenAI(api_key=api_key)

    inicio = datetime.now()
    try:
        total = asyncio.run(recolectar(
            usuario=args.usuario,
            max_comentarios=args.max_comentarios,
            max_segundos=args.max_segundos,
            salida=args.salida,
            cliente_openai=cliente_openai,
        ))
    except KeyboardInterrupt:
        print("\n[ctrl+c] cerrando")
        total = 0

    duracion = (datetime.now() - inicio).total_seconds()
    print(f"\nCapturados {total} comentarios únicos en {duracion:.0f}s → {args.salida}")

    if args.append_a is not None:
        _anexar_a_principal(args.salida, args.append_a)


if __name__ == "__main__":
    main()
