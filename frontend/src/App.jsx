import { useEffect, useState } from "react";
import { api } from "./api.js";
import Live from "./componentes/Live.jsx";
import Analizar from "./componentes/Analizar.jsx";
import CargaArchivo from "./componentes/CargaArchivo.jsx";
import PanelModelo from "./componentes/PanelModelo.jsx";
import Datos from "./componentes/Datos.jsx";
import Reporte from "./componentes/Reporte.jsx";

const PANTALLAS = [
  { id: "live",    etiqueta: "Live",            icono: "📡", comp: Live },
  { id: "reporte", etiqueta: "Reporte",         icono: "📊", comp: Reporte },
  { id: "analizar", etiqueta: "Analizar texto", icono: "✏️", comp: Analizar },
  { id: "carga",   etiqueta: "Carga de archivo", icono: "📂", comp: CargaArchivo },
  { id: "modelo",  etiqueta: "Panel del modelo", icono: "🧠", comp: PanelModelo },
  { id: "datos",   etiqueta: "Datos",           icono: "📈", comp: Datos },
];

function Estado() {
  const [salud, setSalud] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    const cargar = () => api.salud().then(setSalud).catch(() => setError(true));
    cargar();
    const i = setInterval(cargar, 15000);
    return () => clearInterval(i);
  }, []);

  if (error) return <div className="status"><span className="status-mal">● API sin conexión</span></div>;
  if (!salud) return <div className="status">Conectando…</div>;
  const ok = salud.estado === "ok";
  return (
    <div className="status">
      <div><span className={ok ? "status-ok" : "status-mal"}>●</span> {ok ? "operativo" : "modelo no cargado"}</div>
      {salud.modelo && <div className="chico" style={{marginTop: 4}}>{salud.modelo}</div>}
      {salud.version && <div className="chico tenue">v{salud.version}</div>}
      <div className="chico tenue" style={{marginTop: 4}}>DB: {salud.base_de_datos}</div>
    </div>
  );
}

export default function App() {
  const [pantalla, setPantalla] = useState("live");
  // Estado compartido para el flujo Live → Reporte
  const [ultimaSesion, setUltimaSesion] = useState(null);
  const Actual = PANTALLAS.find(p => p.id === pantalla).comp;

  // Props que algunas pantallas pueden necesitar.
  const props = pantalla === "live"
    ? { onTerminarSesion: (datos) => { setUltimaSesion(datos); setPantalla("reporte"); } }
    : pantalla === "reporte"
    ? { sesion: ultimaSesion }
    : {};

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="marca">ComentaVenta IA</div>
        <div className="subtitulo">Clasificador de comentarios de TikTok Live</div>
        {PANTALLAS.map(p => (
          <button
            key={p.id}
            className={`nav-item ${pantalla === p.id ? "activo" : ""}`}
            onClick={() => setPantalla(p.id)}
          >
            <span>{p.icono}</span>
            <span>{p.etiqueta}</span>
          </button>
        ))}
        <Estado />
      </aside>

      <main className="contenido">
        <Actual {...props} />
      </main>
    </div>
  );
}
