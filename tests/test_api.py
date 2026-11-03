"""Pruebas de contratos y validaciones del backend."""

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.schemas import validate_text


client = TestClient(app)


def test_validate_text_vacio():
    with pytest.raises(ValueError):
        validate_text("")


def test_validate_text_solo_espacios():
    with pytest.raises(ValueError):
        validate_text("   ")


def test_validate_text_demasiado_largo():
    with pytest.raises(ValueError):
        validate_text("x" * 500)


def test_validate_text_sin_letras():
    with pytest.raises(ValueError):
        validate_text("12345 !!! ???")


def test_validate_text_ok():
    assert validate_text("  yo el 3  ") == "yo el 3"


def test_health_responde():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert "estado" in r.json()


def test_predict_vacio_devuelve_422():
    r = client.post("/api/predict", json={"texto": ""})
    assert r.status_code == 422
    assert "error" in r.json()


def test_predict_sin_texto_devuelve_422():
    r = client.post("/api/predict", json={})
    assert r.status_code == 422


def test_predict_largo_devuelve_422():
    r = client.post("/api/predict", json={"texto": "x" * 500})
    assert r.status_code == 422


def test_predict_campo_extra_devuelve_422():
    r = client.post("/api/predict", json={"texto": "hola", "extra": "no permitido"})
    assert r.status_code == 422
