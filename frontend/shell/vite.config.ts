import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import federation from "@originjs/vite-plugin-federation";
import path from "path";

export default defineConfig({
  plugins: [
    react(),
    federation({
      name: "shell",
      remotes: {
        iwms: "http://localhost:3001/assets/remoteEntry.js",
        uoih: "http://localhost:3006/assets/remoteEntry.js",
        ccvp: "http://localhost:3002/assets/remoteEntry.js",
        lip: "http://localhost:3003/assets/remoteEntry.js",
        pise: "http://localhost:3004/assets/remoteEntry.js",
        wcvp: "http://localhost:3005/assets/remoteEntry.js",
      },
      shared: ["react", "react-dom", "react-router-dom"],
    }),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 3000,
    cors: true,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
  build: {
    target: "esnext",
    minify: true,
    cssCodeSplit: false,
  },
});
