import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The FastAPI service has no CORS policy, so the browser talks to it through this
// same-origin proxy. Trained-mode portfolio scoring can take over a minute.
const api = process.env.GREENPATH_API_URL ?? "http://127.0.0.1:8000";
const proxy = {
  "/api": {
    target: api,
    changeOrigin: true,
    timeout: 300_000,
    proxyTimeout: 300_000,
    rewrite: (path: string) => path.replace(/^\/api/, ""),
  },
};

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, host: "127.0.0.1", proxy },
  preview: { port: 4173, host: "127.0.0.1", proxy },
});
