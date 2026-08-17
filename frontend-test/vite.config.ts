import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

const fallbackProxyTarget = "http://localhost:8000";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "");
  const proxyTarget = env.DENTAI_PROXY_TARGET || fallbackProxyTarget;

  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        "/api": {
          target: proxyTarget,
          changeOrigin: true
        },
        "/health": {
          target: proxyTarget,
          changeOrigin: true
        },
        "/ready": {
          target: proxyTarget,
          changeOrigin: true
        }
      }
    }
  };
});
