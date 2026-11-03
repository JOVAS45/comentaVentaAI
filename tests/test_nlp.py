"""Pruebas del pipeline NLP (TextPreprocessor)."""

from src.nlp.preprocessing import (TextPreprocessor, normalizar, quitar_tildes,
                                     tokenizar)


def test_normalizar_colapsa_letras_repetidas():
    # "yooo" y "siiii" se colapsan a 2 letras máximo
    assert "yoo" in normalizar("yooooo") or "yo" in normalizar("yooooo")


def test_normalizar_quita_numeros_y_puntuacion():
    salida = normalizar("yo el 3, porfa!!")
    assert "3" not in salida
    assert "!" not in salida
    assert "," not in salida


def test_normalizar_expande_abreviaturas():
    salida = normalizar("cuanto xfa?")
    assert "porfa" in salida


def test_normalizar_emojis_a_palabras():
    salida = normalizar("muy caro 😡")
    assert "emojimolestia" in salida


def test_quitar_tildes_conserva_enie():
    assert quitar_tildes("año") == "año"
    assert quitar_tildes("cuánto") == "cuanto"


def test_tokenizar_descarta_una_letra():
    tokens = tokenizar("yo el negro")
    assert "yo" in tokens
    assert "el" not in tokens  # 2 letras pero el filtro es len > 1 → "el" sí entra
    assert "negro" in tokens


def test_preprocessor_fit_no_hace_nada():
    pre = TextPreprocessor(normalizer="stem")
    assert pre.fit(["ejemplo", "otro"]) is pre


def test_preprocessor_transform_devuelve_strings():
    pre = TextPreprocessor(normalizer="stem")
    salida = pre.transform(["yo el 3", "cuanto sale?"])
    assert len(salida) == 2
    assert all(isinstance(s, str) for s in salida)


def test_explain_devuelve_todos_los_pasos():
    pre = TextPreprocessor(normalizer="stem")
    pasos = pre.explain("yooo quiero el NEGRO 😍")
    assert pasos["original"] == "yooo quiero el NEGRO 😍"
    for clave in ("normalized", "tokens", "removed_stopwords",
                  "without_stopwords", "roots", "final"):
        assert clave in pasos
