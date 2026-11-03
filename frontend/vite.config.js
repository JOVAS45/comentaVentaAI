import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Durante `npm run dev` reenviamos /api al backend FastAPI (puerto 8000).
// En producción nginx cumple ese rol; ver nginx.conf.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.API_URL || "http://localhost:8000",
        changeOrigin: true,
        ws: true,
      },
    },
  },
});
