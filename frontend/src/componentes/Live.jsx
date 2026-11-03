import { useEffect, useRef, useState } from "react";
import { abrirLive } from "../api.js";
import { CLASES, metaDe } from "../clases.js";

/* Pantalla principal: ingresa @usuario, conecta al WebSocket y muestra el panel
   en tiempo real con contadores, feed y pedidos destacados. */
export default function Live({ onTerminarSesion }) {
  const [usuario, setUsuario] = useState("");
  const [estado, setEstado] = useState("inactivo"); // inactivo | conectando | vivo | error
  const [mensaje, setMensaje] = useState("");
  const [comentarios, setComentarios] = useState([]);
  const [filtro, setFiltro] = useState("todas");
  const [inicio, setInicio] = useState(null);
  const [alerta, setAlerta] = useState(null);
  const wsRef = useRef(null);

  // Al desmontar, cerramos WS.
  useEffect(() => () => wsRef.current?.close(), []);

  // Detecta repeticiones de una clase en los últimos 60 s para disparar alerta.
  useEffect(() => {
    if (estado !== "vivo") return;
    const ahora = Date.now();
    const ventana = comentarios.filter(c => (ahora - c.timestamp) < 60_000);
    const porClase = {};
    for (const c of ventana) porClase[c.clase] = (porClase[c.clase] || 0) + 1;
    const [top] = Object.entries(porClase).sort((a, b) => b[1] - a[1]);
    if (top && top[1] >= 8 && top[0] !== "Otros") {
      setAlerta(`${top[1]} ${metaDe(top[0]).etiqueta.toLowerCase()}s en el último minuto`);
    } else {
      setAlerta(null);
    }
  }, [comentarios, estado]);

  const conectar = () => {
    if (!usuario.trim()) {
      setMensaje("Pegá el link de tu live o tu @usuario.");
      return;
    }
    setMensaje("");
    setComentarios([]);
    setEstado("conectando");
    setInicio(Date.now());

    const ws = abrirLive(usuario);
    wsRef.current = ws;

    ws.onmessage = (evento) => {
      let data;
      try { data = JSON.parse(evento.data); } catch { return; }
      if (data.tipo === "conectado") setEstado("vivo");
      else if (data.tipo === "comentario") {
        setComentarios(prev => [{ ...data, timestamp: Date.now() }, ...prev].slice(0, 500));
      } else if (data.tipo === "desconectado") {
        setEstado("inactivo");
        setMensaje(data.razon || "Live terminado.");
      } else if (data.tipo === "error") {
        setEstado("error");
        setMensaje(data.mensaje || "Error del servidor.");
      }
    };
    ws.onerror = () => { setEstado("error"); setMensaje("No se pudo conectar al servidor."); };
    ws.onclose = () => { if (estado === "conectando") setEstado("inactivo"); };
  };

  const terminar = () => {
    try { wsRef.current?.send(JSON.stringify({ accion: "detener" })); } catch {}
    wsRef.current?.close();
    const resumen = {
      usuario: usuario.replace(/^@/, ""),
      iniciada: inicio,
      terminada: Date.now(),
      comentarios: [...comentarios].reverse(),
    };
    setEstado("inactivo");
    onTerminarSesion?.(resumen);
  };

  const contadores = CLASES.reduce((acc, c) => {
    acc[c] = comentarios.filter(x => x.clase === c).length;
    return acc;
  }, {});

  const visibles = filtro === "todas" ? comentarios : comentarios.filter(c => c.clase === filtro);
  const pedidos = comentarios.filter(c => c.clase === "Pedido");

  return (
    <div className="stack">
      <header className="row-entre">
        <div>
          <h1 className="titulo-grande">Live</h1>
          <p className="subtexto">Clasificación en tiempo real de los comentarios del chat.</p>
        </div>
        {estado === "vivo" && <span><span className="punto-estado vivo" /> en vivo</span>}
      </header>

      <div className="card">
        <div className="row">
          <input
            type="text"
            placeholder="@usuario de TikTok o link del live"
            value={usuario}
            onChange={(e) => setUsuario(e.target.value)}
            disabled={estado === "vivo" || estado === "conectando"}
            style={{ flex: 1, minWidth: 240 }}
          />
          {estado === "vivo"
            ? <button className="boton-primario" onClick={terminar}>Terminar análisis</button>
            : <button className="boton-primario" onClick={conectar} disabled={estado === "conectando"}>
                {estado === "conectando" ? "Conectando…" : "Empezar a analizar"}
              </button>}
        </div>
        {mensaje && <div className={estado === "error" ? "error" : "subtexto"} style={{marginTop: 10}}>{mensaje}</div>}
        {alerta && <div className="alerta">⚡ {alerta}</div>}
      </div>

      {estado === "vivo" || comentarios.length > 0 ? (
        <>
          <div className="grid grid-5">
            {CLASES.map(c => {
              const m = metaDe(c);
              return (
                <div key={c} className="contador-clase" style={{ borderColor: m.color }}>
                  <div className="numero" style={{ color: m.color }}>{contadores[c]}</div>
                  <div className="nombre">{m.icono} {m.etiqueta}</div>
                </div>
              );
            })}
          </div>

          <div className="row">
            <button className={`chip ${filtro === "todas" ? "activo" : ""}`} onClick={() => setFiltro("todas")}>
              Todas ({comentarios.length})
            </button>
            {CLASES.map(c => (
              <button key={c} className="chip" onClick={() => setFiltro(c)}
                style={filtro === c ? { borderColor: metaDe(c).color, color: metaDe(c).color } : {}}>
                {metaDe(c).icono} {metaDe(c).etiqueta} ({contadores[c]})
              </button>
            ))}
          </div>

          <div className="grid grid-2">
            <section>
              <h3>Bandeja de comentarios</h3>
              <div className="feed">
                {visibles.length === 0 && <p className="tenue">Esperando comentarios…</p>}
                {visibles.map((c, i) => {
                  const m = metaDe(c.clase);
                  return (
                    <div key={i} className="feed-item" style={{ borderLeftColor: m.color }}>
                      <div style={{ flex: 1 }}>
                        {c.autor && <div className="autor">@{c.autor}</div>}
                        <div className="texto">{c.texto}</div>
                        <div className="meta">
                          <span style={{ color: m.color, fontWeight: 600 }}>{m.icono} {m.etiqueta}</span>
                          {" · "}
                          <span>{Math.round(c.probabilidad * 100)}%</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>

            <section className="destacado-pedidos">
              <h3>🛒 Pedidos ({pedidos.length})</h3>
              {pedidos.length === 0 && <p className="tenue">Todavía no hay pedidos.</p>}
              {pedidos.slice(0, 10).map((p, i) => (
                <div key={i} className="feed-item" style={{ borderLeftColor: metaDe("Pedido").color, marginBottom: 6 }}>
                  <div style={{ flex: 1 }}>
                    {p.autor && <div className="autor">@{p.autor}</div>}
                    <div className="texto">{p.texto}</div>
                  </div>
                </div>
              ))}
            </section>
          </div>
        </>
      ) : (
        <div className="card" style={{ textAlign: "center", padding: 40 }}>
          <p className="tenue">Ingresá un @usuario de TikTok que esté transmitiendo en vivo para empezar.</p>
        </div>
      )}
    </div>
  );
}
