// Metadatos de las 5 clases. Un único lugar para los colores, íconos y acciones
// sugeridas; cualquier componente que muestre una clase lee de acá.

export const CLASES = ["Pedido", "Pregunta", "PagoEnvio", "Objecion", "Otros"];

export const META = {
  Pedido: {
    etiqueta: "Pedido",
    color: "#10b981",
    colorSuave: "#10b98122",
    icono: "🛒",
    accion: "Anotalo o separá el producto",
  },
  Pregunta: {
    etiqueta: "Pregunta",
    color: "#3b82f6",
    colorSuave: "#3b82f622",
    icono: "❓",
    accion: "Respondé en cámara",
  },
  PagoEnvio: {
    etiqueta: "Pago y envío",
    color: "#a855f7",
    colorSuave: "#a855f722",
    icono: "🚚",
    accion: "Explicá pago y entrega",
  },
  Objecion: {
    etiqueta: "Objeción",
    color: "#f59e0b",
    colorSuave: "#f59e0b22",
    icono: "⚠️",
    accion: "Dale confianza o justificá el precio",
  },
  Otros: {
    etiqueta: "Otros",
    color: "#6b7280",
    colorSuave: "#6b728022",
    icono: "💬",
    accion: "Podés ignorarlo",
  },
};

export function metaDe(clase) {
  return META[clase] || META.Otros;
}
