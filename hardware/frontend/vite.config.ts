import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // host:true -> dashboard bisa dibuka dari HP di WiFi yang sama.
  // proxy -> saat dev, /api & /socket.io diteruskan ke backend :4000, jadi
  // frontend pakai origin sama (relative) persis seperti mode single-port.
  server: {
    host: true,
    port: 5173,
    proxy: {
      "/api": "http://localhost:4000",
      "/socket.io": { target: "http://localhost:4000", ws: true },
    },
  },
});
