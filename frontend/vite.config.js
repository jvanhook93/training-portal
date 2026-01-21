import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ command }) => {
  const isDev = command === "serve"; // npm run dev
  return {
    plugins: [react()],

    // Dev: normal URLs (http://localhost:5173/app/)
    // Build: Django-served static (http://<backend>/static/app/...)
    base: isDev ? "/" : "/static/app/",

    build: {
      outDir: "../static/app",
      assetsDir: "assets",
      emptyOutDir: true,
    },
  };
});
