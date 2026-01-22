import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(() => {
  const isCloudflare = process.env.CF_PAGES === "1";

  return {
    plugins: [react()],
    // IMPORTANT:
    // - Cloudflare Pages wants "/" because it serves from site root
    // - Django (Railway) serves built assets from /static/app/
    base: isCloudflare ? "/" : "/static/app/",
    build: {
      // Cloudflare expects dist/ in the frontend project directory
      outDir: isCloudflare ? "dist" : "../static/app",
      assetsDir: "assets",
      emptyOutDir: true,
    },
  };
});
