import { useMemo } from "react";
import { CLASES, metaDe } from "../clases.js";

/* Pantalla de reporte: se muestra al terminar un live, resume lo capturado y
   permite descargar la planilla de comentarios clasificados. */
export default function Reporte({ sesion }) {
  if (!sesion) {
    return (
      <div className="stack">
        <h1 className="titulo-grande">Reporte</h1>
        <p className="subtexto">Todavía no analizaste ningún live. Andá a la pantalla Live, conectate a un @usuario, y al terminar el análisis volvé acá para ver el reporte.</p>
      </div>
    );
  }

  const duracionMin = ((sesion.terminada - sesion.iniciada) / 60000);
  const total = sesion.comentarios.length;

  const porClase = useMemo(() => {
    const acc = Object.fromEntries(CLASES.map(c => [c, 0]));
    for (const c of sesion.comentarios) acc[c.clase] = (acc[c.clase] || 0) + 1;
    return acc;
  }, [sesion]);

  const pedidos = sesion.comentarios.filter(c => c.clase === "Pedido");
  const palabrasRepetidas = (clase, topN = 8) => {
    const cnt = {};
    const stop = new Set(["el", "la", "los", "las", "un", "una", "de", "del", "en", "a", "al", "y", "o", "es", "lo", "me", "mi", "tu", "se", "con", "por", "para", "que", "si", "no"]);
    for (const c of sesion.comentarios.filter(x => x.clase === clase)) {
      for (const p of c.texto.toLowerCase().split(/\s+/)) {
        const limpio = p.replace(/[^\wñáéíóú]/g, "");
        if (limpio.length > 2 && !stop.has(limpio)) cnt[limpio] = (cnt[limpio] || 0) + 1;
      }
    }
    return Object.entries(cnt).sort((a, b) => b[1] - a[1]).slice(0, topN);
  };

  const descargar = () => {
    const encabezado = "autor,texto,clase,probabilidad\n";
    const filas = sesion.comentarios.map(c =>
      [c.autor || "", `"${(c.texto || "").replace(/"/g, '""')}"`, c.clase, c.probabilidad].join(",")
    ).join("\n");
    const blob = new Blob([encabezado + filas], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `live_${sesion.usuario}_${Date.now()}.csv`;
    a.click();
  };

  return (
    <div className="stack">
      <header className="row-entre">
        <div>
          <h1 className="titulo-grande">Reporte del live</h1>
          <p className="subtexto">@{sesion.usuario} · {duracionMin.toFixed(1)} min · {total} comentarios</p>
        </div>
        <button className="boton-primario" onClick={descargar}>Descargar CSV</button>
      </header>

      <section>
        <h3>Resumen por clase</h3>
        <div className="grid grid-5">
          {CLASES.map(c => {
            const m = metaDe(c);
            const n = porClase[c];
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
        <h3>Pedidos detectados ({pedidos.length})</h3>
        {pedidos.length === 0
          ? <p className="tenue">No hubo pedidos en este live.</p>
          : <div className="tabla-scroll">
              <table>
                <thead><tr><th>Autor</th><th>Comentario</th><th>Prob</th></tr></thead>
                <tbody>
                  {pedidos.map((p, i) => (
                    <tr key={i}>
                      <td className="tenue">@{p.autor || "—"}</td>
                      <td>{p.texto}</td>
                      <td className="mono">{Math.round(p.probabilidad * 100)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>}
      </section>

      <section className="grid grid-2">
        <div className="card">
          <h3>Palabras más repetidas en Preguntas</h3>
          <div className="row">
            {palabrasRepetidas("Pregunta").map(([p, n]) => (
              <span key={p} className="chip">{p} <span className="tenue">×{n}</span></span>
            ))}
          </div>
        </div>
        <div className="card">
          <h3>Palabras más repetidas en Objeciones</h3>
          <div className="row">
            {palabrasRepetidas("Objecion").map(([p, n]) => (
              <span key={p} className="chip">{p} <span className="tenue">×{n}</span></span>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
