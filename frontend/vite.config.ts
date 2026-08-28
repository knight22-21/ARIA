import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

// The API target is read from (in order): a .env / .env.local file's VITE_API_TARGET,
// the process env, then a default of :8000. Set VITE_API_TARGET in frontend/.env.local
// once and every `npm run dev` picks it up.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const target = env.VITE_API_TARGET || process.env.VITE_API_TARGET || "http://localhost:8000";
  return {
    plugins: [react()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    server: {
      port: 5173,
      proxy: {
        "/api": {
          target,
          changeOrigin: true,
          rewrite: (p) => p.replace(/^\/api/, ""),
        },
      },
    },
  };
});
