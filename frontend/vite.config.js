import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "/",   // REQUIRED for Cloudflare Pages
  build: {
    outDir: "dist",
    assetsDir: "assets",
  },
});
