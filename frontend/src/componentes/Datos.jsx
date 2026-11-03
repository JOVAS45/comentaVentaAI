import { useEffect, useState } from "react";
import { api } from "../api.js";
import { CLASES, metaDe } from "../clases.js";

export default function Datos() {
  const [metricas, setMetricas] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.metricas().then(setMetricas).catch(e => setError(e.message));
  }, []);

  if (error) return <div className="error">{error}</div>;
  if (!metricas) return <p className="tenue">Cargando…</p>;

  const ds = metricas.dataset;
  const eda = ds.eda;
  const total = Object.values(eda.class_counts).reduce((a, b) => a + b, 0);

  return (
    <div className="stack">
      <header>
        <h1 className="titulo-grande">Datos</h1>
        <p className="subtexto">
          Dataset de entrenamiento: <strong>{total}</strong> comentarios sintéticos de 3 orígenes.
        </p>
      </header>

      <section>
        <h3>Distribución por clase</h3>
        <div className="grid grid-5">
          {CLASES.map(c => {
            const m = metaDe(c);
            const n = eda.class_counts[c] || 0;
            const pct = total > 0 ? (n / total * 100).toFixed(1) : 0;
            return (
              <div key={c} className="contador-clase" style={{ borderColor: m.color }}>
                <div className="numero" style={{ color: m.color }}>{n}</div>
                <div className="nombre">{m.icono} {m.etiqueta}</div>
                <div className="chico tenue">{pct}%</div>
              </div>
            );
          })}
        </div>
      </section>

      <section className="card">
        <h3>Origen de los comentarios</h3>
        <table>
          <thead><tr><th>Fuente</th><th>Comentarios</th></tr></thead>
          <tbody>
            {Object.entries(eda.origin_counts || {}).map(([k, v]) => (
              <tr key={k}>
                <td>
                  {k === "semilla" && "✍️ Semillas escritas a mano"}
                  {k === "gpt-4o-mini" && "🤖 Variantes generadas con GPT-4o-mini"}
                  {k === "tiktok-live" && "📡 Capturados de un live real (TikTokLive)"}
                  {!["semilla", "gpt-4o-mini", "tiktok-live"].includes(k) && k}
                </td>
                <td className="mono">{v}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="card">
        <h3>Longitud de los comentarios (palabras)</h3>
        <table>
          <thead><tr><th>Clase</th><th>Media</th><th>Mediana</th><th>Máximo</th></tr></thead>
          <tbody>
            {CLASES.map(c => {
              const l = eda.length_words[c];
              if (!l) return null;
              return (
                <tr key={c}>
                  <td><span style={{ color: metaDe(c).color }}>{metaDe(c).icono} {metaDe(c).etiqueta}</span></td>
                  <td className="mono">{l.mean}</td>
                  <td className="mono">{l.median}</td>
                  <td className="mono">{l.max}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>

      <section className="card">
        <h3>Palabras más frecuentes por clase</h3>
        <div className="grid grid-3">
          {CLASES.map(c => {
            const top = eda.top_words[c] || [];
            const m = metaDe(c);
            return (
              <div key={c}>
                <h4 style={{ color: m.color, fontSize: "0.95rem" }}>{m.icono} {m.etiqueta}</h4>
                <div className="row">
                  {top.slice(0, 10).map(([palabra, n]) => (
                    <span key={palabra} className="chip">{palabra} <span className="tenue">×{n}</span></span>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      <p className="chico tenue">
        Dataset sintético. Generado con GPT-4o-mini a partir de 100 semillas escritas a mano, complementado con comentarios reales capturados de TikTok Live y auto-etiquetados con el mismo LLM. Semilla aleatoria {metricas.seed}. Entrenado: {metricas.trained_at}.
      </p>
    </div>
  );
}
