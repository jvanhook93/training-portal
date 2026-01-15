import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(() => {
  // On Cloudflare Pages, CF_PAGES is set to "1"
  const isCloudflarePages = process.env.CF_PAGES === "1";

  return {
    plugins: [react()],
    base: isCloudflarePages ? "/" : "/app/",
    build: {
      outDir: "dist",
      assetsDir: "assets",
    },
  };
});
