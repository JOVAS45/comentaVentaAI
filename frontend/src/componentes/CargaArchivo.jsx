import { useState } from "react";
import { api } from "../api.js";
import { CLASES, metaDe } from "../clases.js";

export default function CargaArchivo() {
  const [archivo, setArchivo] = useState(null);
  const [cargando, setCargando] = useState(false);
  const [respuesta, setRespuesta] = useState(null);
  const [error, setError] = useState("");

  const subir = async () => {
    if (!archivo) { setError("Elegí un archivo .csv o .txt."); return; }
    setError(""); setCargando(true); setRespuesta(null);
    try {
      const r = await api.lote(archivo);
      setRespuesta(r);
    } catch (e) {
      setError(e.message);
    } finally {
      setCargando(false);
    }
  };

  const descargarResultados = () => {
    if (!respuesta) return;
    const encabezado = "fila,texto,clase,probabilidad\n";
    const filas = respuesta.resultados.map(r =>
      [r.fila, `"${r.texto.replace(/"/g, '""')}"`, r.clase, r.probabilidad].join(",")
    ).join("\n");
    const blob = new Blob([encabezado + filas], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `comentarios_clasificados_${Date.now()}.csv`;
    a.click();
  };

  return (
    <div className="stack">
      <header>
        <h1 className="titulo-grande">Carga de archivo</h1>
        <p className="subtexto">Subí un .csv (columna <code>texto</code>) o un .txt (un comentario por línea).
          <br />Formato de ejemplo: <a href="/ejemplo_batch.csv" download>descargar ejemplo_batch.csv</a>
        </p>
      </header>

      <div className="card">
        <div className="row">
          <input
            type="file"
            accept=".csv,.txt"
            onChange={(e) => setArchivo(e.target.files?.[0] || null)}
          />
          <button className="boton-primario" onClick={subir} disabled={cargando || !archivo}>
            {cargando ? "Procesando…" : "Clasificar"}
          </button>
        </div>
        <p className="chico tenue" style={{ marginTop: 8 }}>Máximo: 500 filas, 1 MB.</p>
        {error && <div className="error">{error}</div>}
      </div>

      {respuesta && (
        <>
          <div className="row-entre">
            <h3>Resumen ({respuesta.total} clasificados, {respuesta.omitidas.length} omitidos)</h3>
            <button onClick={descargarResultados}>Descargar resultados</button>
          </div>
          <div className="grid grid-5">
            {CLASES.map(c => {
              const m = metaDe(c);
              const n = respuesta.resumen[c] || 0;
              return (
                <div key={c} className="contador-clase" style={{ borderColor: m.color }}>
                  <div className="numero" style={{ color: m.color }}>{n}</div>
                  <div className="nombre">{m.icono} {m.etiqueta}</div>
                </div>
              );
            })}
          </div>

          <div className="card tabla-scroll">
            <table>
              <thead>
                <tr><th>#</th><th>Comentario</th><th>Clase</th><th>Prob</th></tr>
              </thead>
              <tbody>
                {respuesta.resultados.map(r => {
                  const m = metaDe(r.clase);
                  const bajaConf = r.probabilidad < 0.5;
                  return (
                    <tr key={r.fila} style={bajaConf ? { opacity: 0.65 } : {}}>
                      <td className="tenue">{r.fila}</td>
                      <td>{r.texto}</td>
                      <td><span style={{ color: m.color, fontWeight: 600 }}>{m.icono} {m.etiqueta}</span></td>
                      <td className="mono">{Math.round(r.probabilidad * 100)}%</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {respuesta.omitidas.length > 0 && (
            <div className="card">
              <h3>Filas omitidas</h3>
              <table>
                <thead><tr><th>#</th><th>Motivo</th></tr></thead>
                <tbody>
                  {respuesta.omitidas.map(o => (
                    <tr key={o.fila}><td className="tenue">{o.fila}</td><td>{o.motivo}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
