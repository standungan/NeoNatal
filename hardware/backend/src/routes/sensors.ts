import { Router } from "express";
import type { Server } from "socket.io";
import { pool } from "../db.js";
import { readingSchema } from "../validation.js";

const COLUMNS = "id, incubator_id, baby_id, sensors, created_at";

export function sensorRoutes(io: Server): Router {
  const router = Router();

  // ESP8266 -> satu payload lengkap. Simpan 1 row, broadcast ke room incubator.
  router.post("/sensors", async (req, res) => {
    const parsed = readingSchema.safeParse(req.body);
    if (!parsed.success) {
      return res.status(400).json({ error: "invalid payload", details: parsed.error.flatten() });
    }
    const { incubator_id, baby_id, sensors } = parsed.data;
    try {
      const { rows } = await pool.query(
        `INSERT INTO readings (incubator_id, baby_id, sensors)
         VALUES ($1, $2, $3) RETURNING ${COLUMNS}`,
        [incubator_id, baby_id, sensors]
      );
      io.to(incubator_id).emit("reading", rows[0]);
      res.status(201).json(rows[0]);
    } catch (err) {
      console.error("POST /sensors failed", err);
      res.status(500).json({ error: "db error" });
    }
  });

  // Reading terakhir untuk satu incubator (atau baby) — load awal dashboard.
  router.get("/sensors/latest", async (req, res) => {
    const { incubator_id, baby_id } = req.query;
    // ponytail: kolom dipilih dari whitelist, bukan dirangkai dari input -> aman injeksi.
    const column = incubator_id ? "incubator_id" : baby_id ? "baby_id" : null;
    const value = incubator_id ?? baby_id;
    if (!column || typeof value !== "string") {
      return res.status(400).json({ error: "incubator_id or baby_id required" });
    }
    try {
      const { rows } = await pool.query(
        `SELECT ${COLUMNS} FROM readings WHERE ${column} = $1 ORDER BY created_at DESC LIMIT 1`,
        [value]
      );
      res.json(rows[0] ?? null);
    } catch (err) {
      console.error("GET /sensors/latest failed", err);
      res.status(500).json({ error: "db error" });
    }
  });

  return router;
}
