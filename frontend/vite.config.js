import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(() => {
  const isCloudflare = process.env.CF_PAGES === "1";

  return {
    plugins: [react()],
    // Cloudflare Pages serves at site root
    // Django serves built assets under /static/app/
    base: isCloudflare ? "/" : "/static/app/",
    build: {
      // Cloudflare expects dist
      // Django expects to land directly in backend/static/app
      outDir: isCloudflare ? "dist" : "../static/app",
      assetsDir: "assets",
      emptyOutDir: true,
    },
  };
});
