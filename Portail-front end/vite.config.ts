import react from "@vitejs/plugin-react";
import path from "path";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  server: {
    port: 5173,
    proxy: {
      // Les appels /api/* du front sont relayés vers le backend FastAPI local.
      // 127.0.0.1 explicitement, et non « localhost » : Node le résout d'abord
      // en IPv6 (::1) alors qu'uvicorn n'écoute qu'en IPv4 par défaut — le
      // proxy renverrait alors des 500 sans que le backend soit en cause.
      "/api": { target: "http://127.0.0.1:8001", changeOrigin: true },
    },
  },
});
