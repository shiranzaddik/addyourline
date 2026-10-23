import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development the frontend runs on :5173 and proxies API + WebSocket calls to
// the FastAPI backend on :8000, so the browser always talks to a single origin
// (just like the single-domain production deploy).
// Backend origin for the dev proxy. Override with VITE_BACKEND_URL (e.g. in
// Docker Compose where the backend is reachable at http://backend:8000).
const backend = process.env.VITE_BACKEND_URL || "http://localhost:8000";
const backendWs = backend.replace(/^http/, "ws");

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    proxy: {
      "/api": {
        target: backend,
        changeOrigin: true,
      },
      "/ws": {
        target: backendWs,
        ws: true,
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
  },
});
