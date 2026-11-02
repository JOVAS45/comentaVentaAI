"""Preprocesamiento de texto para comentarios de live en español boliviano.

El mismo objeto ``TextPreprocessor`` se usa para entrenar el modelo y, dentro
del pipeline serializado, para atender cada request de la API. La API nunca
reimplementa estos pasos: los ejecuta el primer paso del Pipeline guardado.

Pasos, en orden:
    1. normalizar     minúsculas, URLs, menciones, emojis, números, abreviaturas,
                      alargamientos ("yooo" -> "yo") y puntuación
    2. tokenizar      cortar el texto normalizado en palabras
    3. stop words     quitar palabras sin información para la tarea
    4. stem / lemma   reducir cada palabra a su raíz (Snowball) o lema (spaCy)
    5. tildes         sacar tildes al final para que "cuánto" == "cuanto"
"""

import re
import unicodedata
from functools import lru_cache

import emoji
from sklearn.base import BaseEstimator, TransformerMixin

URL_RE = re.compile(r"https?://\S+|www\.\S+")
MENTION_RE = re.compile(r"@\w+")
# Números y precios: "50", "80 bs", "talla 38". Se reemplazan por un espacio.
NUMBER_RE = re.compile(r"\d+([.,/:]\d+)*%?")
# Alargamientos informales de chat: "yooo" -> "yo", "siiii" -> "si". En español
# ninguna palabra tiene la misma letra 3 veces seguidas.
ELONGATION_RE = re.compile(r"(\w)\1{2,}")
NON_LETTER_RE = re.compile(r"[^a-záéíóúüñ_\s]")
SPACES_RE = re.compile(r"\s+")

# Abreviaturas típicas del chat boliviano. Expandir una abreviatura hace que
# "xfa" y "porfa" sean el mismo token (y luego se quiten como stop word).
# Puede sobrescribirse al construir el TextPreprocessor con `abbreviations=`.
ABREVIATURAS_DEFAULT = {
    "xfa": "porfa", "porfa": "porfa", "plis": "porfa", "plz": "porfa",
    "xq": "porque", "pq": "porque", "porqe": "porque",
    "tbn": "tambien", "tmb": "tambien",
    "q": "que", "k": "que",
    "qro": "quiero", "qiero": "quiero",
    "x": "por",
    "ptm": "", "xd": "", "xdd": "",
    "bs": "bs",  # bolivianos: lo conservamos como palabra para marcar precio
}

# Emojis con carga semántica para esta tarea. Se convierten en una palabra para
# que el vectorizador los trate como feature. Los no listados se eliminan.
EMOJI_WORDS = {
    # Interés positivo / cierre de compra
    "emojiinteres": "😍🔥❤️❤♥👌💯🙏✨🤩💖💜💛💚💙",
    # Molestia / objeción
    "emojimolestia": "😡🤬😤😒🙄😩😫😠😞💔😢😭👎",
    # Celebración / saludo (típico de Otros)
    "emojialegria": "😊😁😄😃🥰🤗😆🤣😂🌟💃🕺👋🙌🎉",
    # Dinero (refuerza contexto comercial)
    "emojidinero": "💰💵💳🏦",
}
EMOJI_TO_WORD = {e: palabra for palabra, chars in EMOJI_WORDS.items() for e in chars}

STOPWORD_LISTS = ("spacy_full", "adjusted")
NORMALIZERS = ("stem", "lemma")


def quitar_tildes(texto: str) -> str:
    """Quita tildes pero conserva la ñ: 'año' y 'ano' son palabras distintas."""
    texto = texto.replace("ñ", "\0")
    texto = "".join(c for c in unicodedata.normalize("NFD", texto)
                    if unicodedata.category(c) != "Mn")
    return texto.replace("\0", "ñ")


def _emoji_a_palabra(chars: str, _data: dict) -> str:
    # chr(0xFE0F) es el "variation selector" que a veces viene pegado al emoji.
    return f" {EMOJI_TO_WORD.get(chars.replace(chr(0xFE0F), ''), '')} "


def normalizar(texto: str, abreviaturas: dict | None = None) -> str:
    """Paso 1. Las tildes se conservan acá porque el lematizador las necesita."""
    if abreviaturas is None:
        abreviaturas = ABREVIATURAS_DEFAULT
    texto = texto.lower()
    texto = URL_RE.sub(" ", texto)
    texto = MENTION_RE.sub(" ", texto)
    texto = texto.replace("#", " ")
    texto = emoji.replace_emoji(texto, replace=_emoji_a_palabra)
    texto = NUMBER_RE.sub(" ", texto)
    texto = ELONGATION_RE.sub(r"\1", texto)
    texto = NON_LETTER_RE.sub(" ", texto)
    palabras = [abreviaturas.get(w, w) for w in texto.split()]
    return SPACES_RE.sub(" ", " ".join(palabras)).strip()


def tokenizar(normalizado: str) -> list[str]:
    """Paso 2. Después de normalizar solo quedan letras y espacios; alcanza con
    partir por espacios. Se descartan tokens de una sola letra ('a', 'y', 'o')."""
    return [t for t in normalizado.split(" ") if len(t) > 1]


@lru_cache
def stopwords_set(nombre: str, keep_words: tuple = (), extra: tuple = ()) -> frozenset:
    """Paso 3. Lista de stop words de spaCy en español, opcionalmente ajustada.

    Las palabras se guardan sin tildes y se comparan sin tildes, porque la gente
    las omite seguido ('mas', 'tambien', 'cuanto').
    """
    from spacy.lang.es.stop_words import STOP_WORDS

    if nombre not in STOPWORD_LISTS:
        raise ValueError(f"Lista de stop words desconocida: {nombre}")
    palabras = {quitar_tildes(w) for w in STOP_WORDS}
    if nombre == "adjusted":
        palabras -= {quitar_tildes(w) for w in keep_words}
        palabras |= {quitar_tildes(w) for w in extra}
    return frozenset(palabras)


@lru_cache
def _stemmer():
    from nltk.stem import SnowballStemmer
    return SnowballStemmer("spanish")


@lru_cache
def _spacy_nlp():
    import spacy
    # No necesitamos parser ni NER para lematizar.
    return spacy.load("es_core_news_sm", disable=["parser", "ner"])


def _es_marcador(token: str) -> bool:
    """True si el token es un marcador especial (emoji convertido) que no se
    debe lematizar ni stemmear."""
    return token.startswith("emoji")


class TextPreprocessor(BaseEstimator, TransformerMixin):
    """Transformer de scikit-learn: textos crudos entran, strings preprocesados salen.

    No aprende nada de los datos (``fit`` no hace nada), por eso aplicarlo antes
    de la validación cruzada no filtra información entre folds.
    """

    def __init__(self, normalizer: str = "lemma", stopword_list: str = "adjusted",
                 keep_words: tuple = (), extra_stopwords: tuple = (),
                 abbreviations: dict | None = None):
        self.normalizer = normalizer
        self.stopword_list = stopword_list
        self.keep_words = keep_words
        self.extra_stopwords = extra_stopwords
        self.abbreviations = abbreviations

    def fit(self, X, y=None):
        if self.normalizer not in NORMALIZERS:
            raise ValueError(f"normalizer debe ser uno de {NORMALIZERS}")
        if self.stopword_list not in STOPWORD_LISTS:
            raise ValueError(f"stopword_list debe ser uno de {STOPWORD_LISTS}")
        return self

    def transform(self, X) -> list[str]:
        return [" ".join(pasos["final"]) for pasos in self._analizar(list(X))]

    def explain(self, texto: str) -> dict:
        """Todos los pasos intermedios para un texto, para la API y el frontend."""
        return self._analizar([texto])[0]

    def _stopwords(self) -> frozenset:
        return stopwords_set(self.stopword_list, tuple(self.keep_words),
                             tuple(self.extra_stopwords))

    def _raices(self, listas_tokens: list[list[str]]) -> list[list[str]]:
        """Paso 4 sobre todos los tokens, antes de quitar stop words, para que
        spaCy vea cada palabra en su contexto de oración."""
        if self.normalizer == "stem":
            stem = _stemmer().stem
            return [[t if _es_marcador(t) else stem(t) for t in tokens]
                    for tokens in listas_tokens]

        from spacy.tokens import Doc
        nlp = _spacy_nlp()
        docs = (Doc(nlp.vocab, words=tokens) for tokens in listas_tokens)
        return [[t.text if _es_marcador(t.text) else t.lemma_.lower() for t in doc]
                for doc in nlp.pipe(docs, batch_size=256)]

    def _analizar(self, textos: list[str]) -> list[dict]:
        abbrs = self.abbreviations if self.abbreviations else ABREVIATURAS_DEFAULT
        normalizados = [normalizar(t or "", abbrs) for t in textos]
        listas_tokens = [tokenizar(n) for n in normalizados]
        listas_raices = self._raices(listas_tokens)
        stop = self._stopwords()

        resultados = []
        for texto, norm, tokens, raices in zip(textos, normalizados, listas_tokens, listas_raices):
            conservados = [(t, r) for t, r in zip(tokens, raices)
                           if quitar_tildes(t) not in stop]
            resultados.append({
                "original": texto,
                "normalized": norm,
                "tokens": tokens,
                "removed_stopwords": [t for t in tokens if quitar_tildes(t) in stop],
                "without_stopwords": [t for t, _ in conservados],
                "roots": [r for _, r in conservados],
                "final": [quitar_tildes(r) for _, r in conservados],
            })
        return resultados
