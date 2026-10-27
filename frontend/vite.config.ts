import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const root = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      input: {
        main: path.join(root, "index.html"),
        cards: path.join(root, "cards.html"),
      },
    },
  },
  server: {
    proxy: {
      "/api": `http://127.0.0.1:${process.env.PLAYWRIGHT_BACKEND_PORT ?? "5000"}`,
    },
  },
});
