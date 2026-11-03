"""Smoke test del endpoint /api/predict con comentarios variados."""
import json
import urllib.request

EJEMPLOS = [
    "mio el 3 porfa",
    "cuanto sale el negro?",
    "aceptan Tigo Money?",
    "muy caro para ser imitacion",
    "holaa desde Cotoca",
    "yooo quiero el 3",
    "la 7 en talla M",
    "envian a Montero?",
    "es original?",
    "mio 80 bs",
]

for t in EJEMPLOS:
    req = urllib.request.Request(
        "http://localhost:8000/api/predict",
        data=json.dumps({"texto": t}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        d = json.loads(r.read())
    print(f"  [{d['clase']:10s} {d['probabilidad']*100:3.0f}%]  {t}")
