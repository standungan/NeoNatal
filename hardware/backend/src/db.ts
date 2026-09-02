import { Pool } from "pg";

export const pool = new Pool({ connectionString: process.env.DATABASE_URL });

// ponytail: auto-init on boot instead of a migration tool — one table, IF NOT EXISTS.
// Swap to a real migration runner (node-pg-migrate) only when the schema starts changing.
export async function initDb(): Promise<void> {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS readings (
      id            BIGSERIAL PRIMARY KEY,
      incubator_id  TEXT        NOT NULL,
      baby_id       TEXT        NOT NULL,
      sensors       JSONB       NOT NULL,
      created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    CREATE INDEX IF NOT EXISTS idx_readings_incubator ON readings (incubator_id, created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_readings_baby      ON readings (baby_id,      created_at DESC);
  `);
}
