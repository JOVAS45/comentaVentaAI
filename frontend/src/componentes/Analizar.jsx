import { useState } from "react";
import { api } from "../api.js";
import { CLASES, metaDe } from "../clases.js";

const EJEMPLOS = [
  "yo el 3 en talla M",
  "cuanto sale el negro?",
  "envian a Montero?",
  "muy caro 😒",
  "holaa desde Cotoca 👋",
];

const PASOS_META = {
  original:              { nombre: "Texto original",       descripcion: "Lo que escribió el usuario." },
  normalizado:           { nombre: "Normalizado",          descripcion: "Minúsculas, URLs y números fuera, emojis convertidos en palabras, abreviaturas expandidas." },
  tokens:                { nombre: "Tokens",               descripcion: "Palabras separadas." },
  stopwords_eliminadas:  { nombre: "Stop words quitadas",  descripcion: "Palabras muy comunes que no aportan información." },
  sin_stopwords:         { nombre: "Sin stop words",       descripcion: "Lo que queda tras filtrar." },
  raices:                { nombre: "Raíces / lemas",       descripcion: "Reducidas a su forma base." },
  final:                 { nombre: "Final (sin tildes)",   descripcion: "Lo que recibe el vectorizador TF-IDF." },
};

export default function Analizar() {
  const [texto, setTexto] = useState("");
  const [cargando, setCargando] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [error, setError] = useState("");

  const analizar = async (txt) => {
    const t = (txt ?? texto).trim();
    if (!t) { setError("Escribe un comentario."); return; }
    setError(""); setCargando(true); setResultado(null);
    try {
      const r = await api.predecir(t);
      setResultado(r);
    } catch (e) {
      setError(e.message);
    } finally {
      setCargando(false);
    }
  };

  const usarEjemplo = (ej) => { setTexto(ej); analizar(ej); };

  const excedido = texto.length > 300;

  return (
    <div className="stack">
      <header>
        <h1 className="titulo-grande">Analizar un comentario</h1>
        <p className="subtexto">Probá un texto suelto y mirá cómo el sistema lo procesa paso a paso.</p>
      </header>

      <div className="card">
        <textarea
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          placeholder="Escribí un comentario como si lo hubiera puesto alguien en tu live…"
          maxLength={320}
        />
        <div className={`contador-chars ${excedido ? "excedido" : ""}`}>{texto.length} / 300</div>
        <div className="row" style={{ marginTop: 12 }}>
          <button className="boton-primario" onClick={() => analizar()} disabled={cargando || excedido || !texto.trim()}>
            {cargando ? "Analizando…" : "Analizar"}
          </button>
          <span className="tenue chico">Ejemplos:</span>
          {EJEMPLOS.map(ej => (
            <button key={ej} className="chip" onClick={() => usarEjemplo(ej)} disabled={cargando}>{ej}</button>
          ))}
        </div>
        {error && <div className="error">{error}</div>}
      </div>

      {resultado && <Resultado resultado={resultado} />}
    </div>
  );
}

function Resultado({ resultado }) {
  const m = metaDe(resultado.clase);
  const pr = resultado.probabilidades;
  const ordenadas = CLASES.map(c => [c, pr[c] ?? 0]).sort((a, b) => b[1] - a[1]);

  return (
    <div className="resultado">
      <div className="row-entre">
        <span className="badge-clase" style={{ background: m.colorSuave, color: m.color }}>
          {m.icono} {m.etiqueta}
        </span>
        <div className="probabilidad-grande" style={{ color: m.color }}>
          {Math.round(resultado.probabilidad * 100)}%
        </div>
      </div>

      <p className="tenue" style={{ marginTop: 4 }}>
        Acción sugerida: <strong style={{ color: "var(--texto)" }}>{m.accion}</strong>
      </p>

      <h3>Probabilidad por clase</h3>
      <div className="stack" style={{ gap: 8 }}>
        {ordenadas.map(([c, p]) => {
          const mm = metaDe(c);
          return (
            <div key={c}>
              <div className="row-entre chico">
                <span>{mm.icono} {mm.etiqueta}</span>
                <span className="mono">{(p * 100).toFixed(1)}%</span>
              </div>
              <div className="barra"><span style={{ width: `${p * 100}%`, background: mm.color }} /></div>
            </div>
          );
        })}
      </div>

      <details open>
        <summary>¿Cómo lo entendió el sistema?</summary>
        <div style={{ marginTop: 12 }}>
          {Object.entries(PASOS_META).map(([clave, meta]) => {
            const valor = resultado.preprocesamiento[clave];
            const vista = Array.isArray(valor) ? valor.join(" · ") : valor;
            return (
              <div key={clave} className="paso-nlp">
                <div>
                  <div className="nombre">{meta.nombre}</div>
                  <div className="chico tenue">{meta.descripcion}</div>
                </div>
                <div className="valor">{vista || <span className="tenue">(vacío)</span>}</div>
              </div>
            );
          })}
          <p className="chico tenue" style={{ marginTop: 8 }}>
            Método: <strong>{resultado.preprocesamiento.metodo}</strong> ·
            Modelo: {resultado.modelo.nombre} v{resultado.modelo.version} ·
            Tiempo: {resultado.tiempo_ms} ms
          </p>
        </div>
      </details>
    </div>
  );
}
