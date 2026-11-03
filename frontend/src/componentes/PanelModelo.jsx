import { useEffect, useState } from "react";
import { api } from "../api.js";
import { CLASES, metaDe } from "../clases.js";

export default function PanelModelo() {
  const [metricas, setMetricas] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.metricas().then(setMetricas).catch(e => setError(e.message));
  }, []);

  if (error) return <div className="error">{error}</div>;
  if (!metricas) return <p className="tenue">Cargando métricas…</p>;

  const prod = metricas.production;
  const modelos = metricas.models;

  return (
    <div className="stack">
      <header>
        <h1 className="titulo-grande">Panel del modelo</h1>
        <p className="subtexto">Comparación de los modelos entrenados y métricas del que está en producción.</p>
      </header>

      <div className="card" style={{ borderColor: "var(--acento)", background: "linear-gradient(135deg, var(--acento-suave), transparent)" }}>
        <div className="row-entre">
          <div>
            <div className="chico tenue">EN PRODUCCIÓN</div>
            <h2 style={{ fontSize: "1.4rem", color: "var(--acento)" }}>{prod.label}</h2>
            <p className="chico tenue">
              {prod.config.normalizer} · {prod.config.stopword_list} · n-gramas {prod.config.ngram_range}
            </p>
          </div>
          <div style={{ textAlign: "right" }}>
            <div className="probabilidad-grande">{(prod.cv_f1_macro * 100).toFixed(1)}%</div>
            <div className="chico tenue">F1 macro (CV)</div>
          </div>
        </div>
      </div>

      <section className="card">
        <h3>Comparación de modelos</h3>
        <div className="tabla-scroll">
          <table>
            <thead>
              <tr>
                <th>Modelo</th>
                <th>CV F1 macro</th>
                <th>Test F1 macro</th>
                <th>Test accuracy</th>
              </tr>
            </thead>
            <tbody>
              {modelos.map(m => (
                <tr key={m.name} style={m.name === prod.name ? { background: "var(--acento-suave)" } : {}}>
                  <td>
                    {m.name === prod.name && <span style={{ color: "var(--acento)", marginRight: 4 }}>★</span>}
                    {m.label}
                  </td>
                  <td className="mono">{(m.cv_f1_macro * 100).toFixed(1)}% <span className="chico tenue">±{(m.cv_f1_macro_std * 100).toFixed(1)}</span></td>
                  <td className="mono">{(m.test.f1_macro * 100).toFixed(1)}%</td>
                  <td className="mono">{(m.test.accuracy * 100).toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card">
        <h3>F1 por clase (modelo en producción)</h3>
        <div className="stack" style={{ gap: 10 }}>
          {CLASES.map(c => {
            const perClass = modelos.find(m => m.name === prod.name)?.test.per_class[c];
            if (!perClass) return null;
            const m = metaDe(c);
            return (
              <div key={c}>
                <div className="row-entre chico">
                  <span>{m.icono} {m.etiqueta} <span className="tenue">(n={perClass.support})</span></span>
                  <span className="mono">P {(perClass.precision * 100).toFixed(0)}% · R {(perClass.recall * 100).toFixed(0)}% · F1 {(perClass.f1 * 100).toFixed(0)}%</span>
                </div>
                <div className="barra"><span style={{ width: `${perClass.f1 * 100}%`, background: m.color }} /></div>
              </div>
            );
          })}
        </div>
      </section>

      <section className="card">
        <h3>Matriz de confusión</h3>
        <MatrizConfusion matriz={modelos.find(m => m.name === prod.name)?.test.confusion_matrix} />
      </section>

      <section className="card">
        <h3>Palabras más influyentes por clase</h3>
        <div className="grid grid-3">
          {CLASES.map(c => {
            const top = metricas.top_terms?.[c] || [];
            const m = metaDe(c);
            return (
              <div key={c}>
                <h4 style={{ color: m.color, fontSize: "0.95rem" }}>{m.icono} {m.etiqueta}</h4>
                <div className="row">
                  {top.slice(0, 10).map(([palabra, peso]) => (
                    <span key={palabra} className="chip" title={`peso ${peso}`}>{palabra}</span>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}

function MatrizConfusion({ matriz }) {
  if (!matriz) return <p className="tenue">Sin datos.</p>;
  const n = CLASES.length;
  return (
    <div className="matriz" style={{ gridTemplateColumns: `auto repeat(${n}, 1fr)` }}>
      <div className="celda header"></div>
      {CLASES.map(c => <div key={c} className="celda header">{metaDe(c).etiqueta}</div>)}
      {matriz.map((fila, i) => (
        <>
          <div key={`r${i}`} className="celda header" style={{ textAlign: "right" }}>{metaDe(CLASES[i]).etiqueta}</div>
          {fila.map((v, j) => (
            <div key={`c${i}-${j}`} className={`celda ${i === j ? "diag" : ""}`}>{v}</div>
          ))}
        </>
      ))}
    </div>
  );
}
