export interface Sensors {
  heart_rate?: number;
  spo2?: number;
  ds18b20_temp?: number | null;
  dht22_temp?: number | null;
  dht22_humidity?: number | null;
  [key: string]: number | null | undefined; // sensor lain (JSONB fleksibel)
}

export interface Reading {
  id: number;
  incubator_id: string;
  baby_id: string;
  sensors: Sensors;
  created_at: string;
}

// Satu titik untuk grafik Recharts (waktu sudah diformat).
export interface ChartPoint {
  t: string;
  heart_rate?: number;
  spo2?: number;
  ds18b20_temp?: number;
  dht22_temp?: number;
  dht22_humidity?: number;
}
