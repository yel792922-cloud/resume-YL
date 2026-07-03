import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The frontend talks to the FastAPI backend on :8000; /api is proxied in dev.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
