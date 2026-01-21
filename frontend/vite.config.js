import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(() => {
  const isCloudflare = process.env.CF_PAGES === "1";

  return {
    plugins: [react()],
    base: "/", // Cloudflare wants root-base paths
    build: {
      outDir: isCloudflare ? "dist" : "../static/app",
      assetsDir: "assets",
      emptyOutDir: isCloudflare, // only wipe dist on Cloudflare builds
    },
  };
});
