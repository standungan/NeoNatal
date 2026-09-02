import "dotenv/config";
import express from "express";
import cors from "cors";
import { createServer } from "http";
import { initDb } from "./db.js";
import { createSocket } from "./socket.js";
import { sensorRoutes } from "./routes/sensors.js";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const app = express();
app.use(cors());
app.use(express.json());

const httpServer = createServer(app);
const io = createSocket(httpServer);

app.get("/api/health", (_req, res) => res.json({ ok: true }));
app.use("/api", sensorRoutes(io));

// Serve dashboard (hasil build frontend) dari server yang sama -> satu port,
// satu URL, tanpa CORS. Aktif kalau frontend sudah di-build (frontend/dist).
const frontendDist = join(dirname(fileURLToPath(import.meta.url)), "../../frontend/dist");
if (existsSync(frontendDist)) {
  app.use(express.static(frontendDist));
  app.use((req, res, next) => {
    if (req.method !== "GET" || req.path.startsWith("/api")) return next();
    res.sendFile(join(frontendDist, "index.html")); // SPA fallback
  });
  console.log(`serving dashboard from ${frontendDist}`);
} else {
  console.log("frontend/dist belum ada — `npm run build` di frontend/ untuk serve dashboard di sini");
}

const port = Number(process.env.PORT ?? 4000);

initDb()
  .then(() => httpServer.listen(port, () => console.log(`backend listening on :${port}`)))
  .catch((err) => {
    console.error("db init failed — is PostgreSQL running & DATABASE_URL correct?", err);
    process.exit(1);
  });
