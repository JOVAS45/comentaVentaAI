// Cliente HTTP + WebSocket contra la API FastAPI. En producción nginx proxea
// /api al contenedor api; en desarrollo lo hace Vite (ver vite.config.js).

async function pedir(ruta, opciones) {
  let resp;
  try {
    resp = await fetch(`/api${ruta}`, opciones);
  } catch {
    throw new Error("No se pudo conectar con la API.");
  }
  const cuerpo = await resp.json().catch(() => ({}));
  if (!resp.ok) throw new Error(cuerpo.error || `Error ${resp.status}`);
  return cuerpo;
}

export const api = {
  salud: () => pedir("/health"),
  predecir: (texto) =>
    pedir("/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ texto }),
    }),
  lote: (archivo) => {
    const form = new FormData();
    form.append("archivo", archivo);
    return pedir("/predict/batch", { method: "POST", body: form });
  },
  metricas: () => pedir("/metrics"),
  historial: (limit = 30) => pedir(`/history?limit=${limit}`),
  entrenamientos: () => pedir("/trainings"),
};

/** Abre un WebSocket al endpoint /api/live/{usuario}. Devuelve el objeto WS
 *  listo para que el llamador agregue handlers. */
export function abrirLive(usuario) {
  const limpio = usuario.replace(/^@/, "").trim();
  const protocolo = window.location.protocol === "https:" ? "wss" : "ws";
  const url = `${protocolo}://${window.location.host}/api/live/${encodeURIComponent(limpio)}`;
  return new WebSocket(url);
}
