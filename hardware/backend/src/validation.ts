import { z } from "zod";

// Struktur objek sensors. passthrough(): sensor baru boleh nambah field tanpa
// ubah skema — sejalan dengan alasan pakai JSONB. Field vital diberi rentang wajar.
export const sensorsSchema = z
  .object({
    heart_rate: z.number().min(0).max(300).optional(),
    spo2: z.number().min(0).max(100).optional(),
    ds18b20_temp: z.number().min(-40).max(125).nullable().optional(),
    dht22_temp: z.number().min(-40).max(125).nullable().optional(),
    dht22_humidity: z.number().min(0).max(100).nullable().optional(),
  })
  .passthrough();

export const readingSchema = z.object({
  incubator_id: z.string().min(1),
  baby_id: z.string().min(1),
  sensors: sensorsSchema,
});

export type ReadingInput = z.infer<typeof readingSchema>;
