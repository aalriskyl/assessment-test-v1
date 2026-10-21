import path from "node:path"
import { fileURLToPath } from "node:url"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"
import { defineConfig } from "vite"

const root = path.dirname(fileURLToPath(import.meta.url))

export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: "/static/app/",
  resolve: { alias: { "@": path.resolve(root, "src") } },
  build: {
    outDir: path.resolve(root, "../procurement/static/app"),
    emptyOutDir: true,
    manifest: true,
    rollupOptions: { input: path.resolve(root, "src/main.tsx") },
  },
})
