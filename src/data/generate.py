"""Generador del dataset sintético de ComentaVenta IA.

Expande las semillas escritas a mano (data/raw/semillas.json) en un dataset
de ~2500 comentarios variados usando GPT-4o-mini, respetando la distribución
de clases que imita un live real (muchos "Otros", pocos "Pedido/Objecion").

Uso:
    # Modo real: llama a OpenAI (requiere OPENAI_API_KEY en el entorno)
    python -m src.data.generate

    # Modo mock: no llama a OpenAI; expande con plantillas simples. Útil para
    # probar el pipeline sin gastar tokens.
    python -m src.data.generate --mock

    # Semilla aleatoria y archivo de salida personalizados
    python -m src.data.generate --seed 123 --salida data/raw/otro.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import re
import sys
import time
from pathlib import Path
from typing import Iterable

from src.config import LABELS, ROOT, load_params

SEMILLAS_PATH = ROOT / "data" / "raw" / "semillas.json"
SALIDA_DEFAULT = ROOT / "data" / "raw" / "comentarios.csv"

# Catálogos usados tanto en modo mock como en el prompt del LLM.
BARRIOS = [
    "Plan 3000", "Pampa de la Isla", "Villa 1ro de Mayo", "Cotoca",
    "Montero", "Warnes", "La Guardia", "Urubó", "4to anillo", "2do anillo",
    "Equipetrol", "Las Palmas", "Alto San Pedro", "Satélite Norte",
    "Palmasola", "Doble Vía La Guardia", "Km 7 al norte",
]

PRODUCTOS_DETALLE = {
    "ropa": ["blusa", "polera", "vestido", "jean", "campera", "short", "sweater"],
    "calzado": ["zapatillas", "sandalias", "botines", "tacos", "tenis"],
    "maquillaje": ["labial", "base", "sombra", "rubor", "mascara", "corrector"],
    "accesorios": ["cartera", "mochila", "reloj", "pulsera", "aretes", "gorra"],
    "tecnologia": ["audífono", "celular", "cargador", "parlante", "smartwatch"],
}

COLORES = ["negro", "blanco", "rojo", "azul", "rosado", "verde", "beige",
           "plateado", "dorado", "gris", "vino", "nude", "camel", "fucsia"]

TALLAS_ROPA = ["XS", "S", "M", "L", "XL"]
TALLAS_CALZADO = ["35", "36", "37", "38", "39", "40", "41", "42"]

EMOJIS_POSITIVOS = ["😍", "🔥", "😊", "🙏", "💖", "✨", "💯"]
EMOJIS_NEGATIVOS = ["😡", "😤", "😒", "🙄", "💔"]
EMOJIS_NEUTROS = ["👀", "🤔", "👋", "💃"]

ABREVIATURAS = {
    "por favor": ["xfa", "porfa", "plis", "plz"],
    "porque": ["xq", "pq"],
    "también": ["tbn", "tmb"],
    "que": ["q"],
    "quiero": ["qro"],
}


# ---------- Modo real: llamadas a GPT-4o-mini ----------

PROMPT_SISTEMA = """Eres un generador de comentarios realistas de lives de venta
de TikTok en Santa Cruz de la Sierra, Bolivia. Recibes un comentario semilla
etiquetado con una clase y debes producir N variantes del MISMO tipo (misma
clase), pero con texto distinto.

Las 5 clases y lo que significan:
- Pedido: el usuario quiere comprar o reservar un producto. Formas típicas:
    * "yo", "yo el 3", "yooo", "siii yo"            → quiere el producto que se mostró
    * "mio", "mío"                                   → quiere comprar (subasta boliviana)
    * "mio 50", "mio en 80 bs", "mío 120"           → OFERTA DE PRECIO en bolivianos
    * "lo tomo", "me lo llevo", "lo quiero"          → confirma compra
    * "me lo separas", "resérvame", "me lo guardas"  → pide reservar
- Pregunta: pide información del producto (precio, talla, color, stock, material).
    Ejemplos: "cuanto?", "hay en M?", "es cuero?", "cuanto sale el negro?"
- PagoEnvio: pregunta por formas de pago, envíos o entregas.
    Ejemplos: "aceptan QR?", "envían a Montero?", "cuanto el delivery?",
    "aceptas Tigo Money?", "pago contra entrega?"
- Objecion: expresa algo que frena la compra (precio alto, desconfianza, mala
    experiencia). Ejemplos: "muy caro", "en el mercado está más barato",
    "es original?", "a mi amiga no le llegó", "mi vecina compró y le llegó fallado"
- Otros: sin acción comercial (saludos, elogios, emojis, spam, conversación).
    Ejemplos: "hola desde Cotoca", "🔥🔥", "qué linda", "saludos", "sígueme"

Prioridad para comentarios ambiguos: Pedido > Objecion > PagoEnvio > Pregunta > Otros.
Ejemplo: "está caro pero lo quiero" → Pedido (prioriza la intención de compra).

Reglas de generación:
- Lenguaje INFORMAL BOLIVIANO CRUCEÑO. No uses "vos" argentino; en Bolivia es "tú"
  o "usted". Precios en BOLIVIANOS (bs). Usa barrios reales de Santa Cruz:
  Plan 3000, Pampa de la Isla, Villa 1ro de Mayo, Cotoca, Montero, Warnes,
  La Guardia, Urubó, 4to anillo, 2do anillo, Equipetrol, Palmasola, Satélite Norte.
  También ciudades: Cochabamba, La Paz, El Alto, Sucre, Tarija, Oruro.
- Formas de pago locales: Tigo Money, QR, transferencia bancaria, efectivo,
  contra entrega. (NO uses Yape ni Plin, que son peruanos; en Bolivia es Tigo Money.)
- Varía longitud: desde UNA PALABRA hasta dos oraciones. Muchos comentarios
  son muy cortos: "yo", "mío", "cuanto?", "🔥". No todos tienen que ser oraciones completas.
- Mezcla estilos: algunos normales, otros con abreviaturas (xfa, porfa, pq, xq,
  tbn, q, qro, plis), otros con letras repetidas (yooo, siiii, holaaa), otros
  con emojis, otros en MAYÚSCULAS enteras.
- Pueden incluir typos naturales de chat ("monteroo", "cuantto", "basureo",
  "porqe"). Nunca exageres: 1-2 typos por comentario como máximo.
- Para "Pedido" variá entre: "yo"+ (número o color o talla), "mio" + precio,
  "me lo separas", "lo quiero", "quiero N". El patrón "mío + número" es
  especialmente común en subastas de live.
- Mantén el tipo de producto si la semilla lo tiene (ropa, calzado, maquillaje,
  accesorios, tecnología).
- NO repitas la semilla textualmente ni generes variantes casi idénticas entre sí.
- NO inventes clases nuevas, respetá la clase dada.
- NO uses nombres de personas inventados (@usuario123 etc.), no es necesario.

Devuelve EXCLUSIVAMENTE un JSON object con una clave "variantes" cuyo valor es
un array, sin texto adicional. Ejemplo del formato esperado:
{
  "variantes": [
    {"texto": "...", "estilo": "normal"},
    {"texto": "...", "estilo": "letras_repetidas"},
    {"texto": "...", "estilo": "emojis"}
  ]
}

Valores válidos de "estilo": normal, abreviaturas, emojis, mayusculas, letras_repetidas, mixto.
"""

PROMPT_USUARIO_TPL = """Clase: {clase}
Producto (si aplica): {producto}
Semilla: "{texto}"

Generá {n} variantes distintas de esta semilla, misma clase, lenguaje de live
de TikTok boliviano. Devolvé solo el JSON array."""


def _llamar_openai(cliente, clase: str, semilla: dict, n: int,
                   modelo: str = "gpt-4o-mini") -> list[dict]:
    """Llama a GPT-4o-mini y devuelve las variantes como lista de dicts."""
    producto = semilla.get("producto") or "cualquiera"
    prompt = PROMPT_USUARIO_TPL.format(
        clase=clase, producto=producto, texto=semilla["texto"], n=n,
    )
    respuesta = cliente.chat.completions.create(
        model=modelo,
        temperature=0.9,
        messages=[
            {"role": "system", "content": PROMPT_SISTEMA},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )
    contenido = respuesta.choices[0].message.content
    # El modelo a veces envuelve el array en una clave; aceptamos ambos.
    datos = json.loads(contenido)
    if isinstance(datos, dict):
        for v in datos.values():
            if isinstance(v, list):
                return v
        raise ValueError(f"Respuesta sin array: {datos!r}")
    return datos


# ---------- Modo mock: expansión por plantillas (sin GPT) ----------

def _mock_expandir(semilla: dict, clase: str, n: int, rng: random.Random) -> list[dict]:
    """Variantes simples por manipulación del texto. No usa internet."""
    base = semilla["texto"]
    producto = semilla.get("producto")
    variantes = []
    for _ in range(n):
        texto = base
        estilo = rng.choice(
            ["normal", "abreviaturas", "emojis", "mayusculas", "letras_repetidas", "mixto"]
        )
        # Reemplazar producto genérico si la semilla no tiene uno específico.
        if producto and producto in PRODUCTOS_DETALLE and rng.random() < 0.4:
            detalle = rng.choice(PRODUCTOS_DETALLE[producto])
            texto = f"{texto} {detalle}"
        # Agregar color o talla ocasionalmente.
        if rng.random() < 0.25:
            texto = f"{texto} {rng.choice(COLORES)}"
        if rng.random() < 0.20 and producto in ("ropa", "calzado"):
            tallas = TALLAS_ROPA if producto == "ropa" else TALLAS_CALZADO
            texto = f"{texto} talla {rng.choice(tallas)}"
        # Mencionar barrio ocasionalmente (más probable en PagoEnvio).
        prob_barrio = 0.5 if clase == "PagoEnvio" else 0.15
        if rng.random() < prob_barrio:
            texto = f"{texto} {rng.choice(BARRIOS)}"
        # Aplicar estilo elegido.
        texto = _aplicar_estilo(texto, estilo, clase, rng)
        variantes.append({"texto": texto.strip(), "estilo": estilo})
    return variantes


def _aplicar_estilo(texto: str, estilo: str, clase: str, rng: random.Random) -> str:
    if estilo == "mayusculas":
        return texto.upper()
    if estilo == "letras_repetidas":
        palabras = texto.split()
        if palabras:
            i = rng.randrange(len(palabras))
            p = palabras[i]
            if len(p) > 2:
                letra_idx = len(p) - 2
                palabras[i] = p[:letra_idx] + p[letra_idx] * rng.randint(2, 4) + p[letra_idx+1:]
        return " ".join(palabras)
    if estilo == "abreviaturas":
        for forma, cortes in ABREVIATURAS.items():
            if forma in texto:
                texto = texto.replace(forma, rng.choice(cortes))
        return texto
    if estilo == "emojis":
        emojis = (EMOJIS_NEGATIVOS if clase == "Objecion"
                  else EMOJIS_POSITIVOS if clase in ("Pedido", "Otros")
                  else EMOJIS_NEUTROS)
        n_em = rng.randint(1, 3)
        return texto + " " + "".join(rng.choices(emojis, k=n_em))
    if estilo == "mixto":
        texto = _aplicar_estilo(texto, "abreviaturas", clase, rng)
        return _aplicar_estilo(texto, "emojis", clase, rng)
    return texto


# ---------- Orquestación ----------

def _target_por_clase(params: dict, total: int) -> dict[str, int]:
    distribucion = params.get("class_distribution") or {}
    if not distribucion:
        return {c: total // len(LABELS) for c in LABELS}
    objetivo = {c: int(round(distribucion.get(c, 0) * total)) for c in LABELS}
    # Ajuste si el redondeo no da la suma exacta.
    diff = total - sum(objetivo.values())
    if diff != 0:
        objetivo[LABELS[-1]] += diff
    return objetivo


def _escribir_csv(filas: Iterable[dict], salida: Path) -> int:
    salida.parent.mkdir(parents=True, exist_ok=True)
    campos = ["id", "texto", "clase", "producto", "estilo", "origen"]
    n = 0
    with open(salida, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        for fila in filas:
            writer.writerow(fila)
            n += 1
    return n


def generar(mock: bool, seed: int, salida: Path, total: int,
            origen_override: str | None = None,
            incluir_semillas: bool = True) -> int:
    """Genera el dataset completo y lo escribe en `salida`. Devuelve cuántas filas.

    - `origen_override`: si se pasa, usa esa etiqueta en vez de "gpt-4o-mini"/"mock"
      en la columna `origen` de las variantes. Las semillas conservan "semilla".
    - `incluir_semillas`: si False, no vuelca las semillas al CSV (útil para un
      archivo de ampliación).
    """
    rng = random.Random(seed)
    with open(SEMILLAS_PATH, encoding="utf-8") as f:
        datos = json.load(f)
    semillas_por_clase = {c: datos[c] for c in LABELS}
    params = load_params()
    objetivo = _target_por_clase(params, total)

    cliente = None
    if not mock:
        try:
            from openai import OpenAI
        except ImportError:
            sys.exit("Falta la librería openai. Instalala con `pip install openai` o usá --mock.")
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            sys.exit("Falta OPENAI_API_KEY en el entorno. Exportala o usá --mock.")
        cliente = OpenAI(api_key=api_key)

    filas = []
    id_contador = 1
    for clase in LABELS:
        semillas = semillas_por_clase[clase]
        target = objetivo[clase]
        por_semilla = max(1, target // len(semillas))
        print(f"[{clase}] semillas={len(semillas)} target={target} variantes_por_semilla={por_semilla}")
        # 1) Agregar la semilla misma como un ejemplo real (opcional).
        if incluir_semillas:
            for s in semillas:
                filas.append({
                    "id": id_contador, "texto": s["texto"], "clase": clase,
                    "producto": s.get("producto") or "", "estilo": s.get("estilo") or "normal",
                    "origen": "semilla",
                })
                id_contador += 1
        # 2) Expandir cada semilla con variantes.
        cuenta_clase = len(semillas) if incluir_semillas else 0
        for s in semillas:
            n_variantes = por_semilla
            if cuenta_clase + n_variantes > target:
                n_variantes = max(0, target - cuenta_clase)
            if n_variantes == 0:
                break
            if mock:
                variantes = _mock_expandir(s, clase, n_variantes, rng)
                origen = origen_override or "mock"
            else:
                try:
                    variantes = _llamar_openai(cliente, clase, s, n_variantes)
                    origen = origen_override or "gpt-4o-mini"
                    time.sleep(0.2)  # pequeño rate-limit por cortesía
                except Exception as e:
                    print(f"  [warn] fallo al generar variantes de \"{s['texto']}\": {e}")
                    continue
            estilos_validos = {"normal", "abreviaturas", "emojis",
                               "mayusculas", "letras_repetidas", "mixto"}
            for v in variantes:
                texto = (v.get("texto") or "").strip()
                if not texto:
                    continue
                estilo = v.get("estilo") or "normal"
                if estilo not in estilos_validos:
                    estilo = "normal"  # GPT a veces inventa estilos nuevos
                filas.append({
                    "id": id_contador, "texto": texto, "clase": clase,
                    "producto": s.get("producto") or "",
                    "estilo": estilo,
                    "origen": origen,
                })
                id_contador += 1
                cuenta_clase += 1

    # Deduplicar por texto (preservando orden) y renumerar.
    vistos = set()
    unicas = []
    for f in filas:
        clave = re.sub(r"\s+", " ", f["texto"].lower()).strip()
        if clave in vistos:
            continue
        vistos.add(clave)
        unicas.append(f)
    for i, f in enumerate(unicas, start=1):
        f["id"] = i

    n = _escribir_csv(unicas, salida)
    print(f"\nDataset escrito en {salida}: {n} comentarios únicos")
    conteo = {}
    for f in unicas:
        conteo[f["clase"]] = conteo.get(f["clase"], 0) + 1
    print("Distribución por clase:")
    for c in LABELS:
        print(f"  {c}: {conteo.get(c, 0)}")
    return n


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mock", action="store_true",
                        help="no llama a OpenAI; expande con plantillas (sin costo)")
    parser.add_argument("--seed", type=int, default=None,
                        help="semilla aleatoria (por defecto, la de params.yaml)")
    parser.add_argument("--salida", type=Path, default=SALIDA_DEFAULT,
                        help=f"ruta del CSV de salida (default: {SALIDA_DEFAULT})")
    parser.add_argument("--total", type=int, default=None,
                        help="total objetivo de comentarios (default: n_samples de params.yaml)")
    parser.add_argument("--origen", type=str, default=None,
                        help="etiqueta a usar en la columna 'origen' de las variantes (default: 'gpt-4o-mini')")
    parser.add_argument("--sin-semillas", action="store_true",
                        help="no vuelca las semillas al CSV (útil para archivos de ampliación)")
    args = parser.parse_args()

    params = load_params()
    seed = args.seed if args.seed is not None else params["seed"]
    total = args.total if args.total is not None else params["data"]["n_samples"]
    generar(mock=args.mock, seed=seed, salida=args.salida, total=total,
            origen_override=args.origen, incluir_semillas=not args.sin_semillas)


if __name__ == "__main__":
    main()
