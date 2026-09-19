"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { SensorReading } from "@/lib/types";

const WINDOW = 120;

/**
 * Recent sensor samples for one incubator, oldest first.
 *
 * Live via SSE, with polling as the fallback. EventSource carries the session
 * cookie automatically and the BFF turns that into a Bearer server-side, so the
 * browser needs no token of its own — the reason SSE was chosen over a
 * WebSocket, which would have needed short-lived tickets and a way around the
 * proxy.
 *
 * The initial backfill still comes from GET /readings: the server's ring buffer
 * only holds ~6 minutes, and a chart should open with history rather than
 * filling in from empty.
 *
 * `since` is the start of the incubator's current occupancy. The server already
 * cuts both the backfill and the stream replay there; filtering again here
 * covers a page left open across an admission, whose chart would otherwise keep
 * the previous baby's readings until reloaded.
 */
export function useSensorReadings(incubatorId: string, limit = WINDOW, since?: string) {
  // Backfill. Once the stream is live this stops polling and simply holds the
  // seed data; if the stream never connects, it keeps polling as before.
  const [streaming, setStreaming] = useState(false);

  const backfill = useQuery({
    queryKey: ["readings", incubatorId, limit, since],
    queryFn: async () =>
      (
        await api.get<SensorReading[]>(
          `/incubators/${incubatorId}/readings?limit=${limit}`,
        )
      ).data,
    refetchInterval: streaming ? false : 3_000,
  });

  const [live, setLive] = useState<SensorReading[]>([]);
  const seenIds = useRef<Set<string>>(new Set());

  useEffect(() => {
    // Reset per incubator: navigating between two incubators must not carry
    // one's readings onto the other's chart.
    setLive([]);
    seenIds.current = new Set();
    setStreaming(false);

    if (typeof window === "undefined" || !("EventSource" in window)) return;

    const es = new EventSource(`/api/v1/incubators/${incubatorId}/stream`);

    es.onopen = () => setStreaming(true);

    es.onmessage = (ev) => {
      try {
        const r = JSON.parse(ev.data) as SensorReading;
        // The stream replays its ring buffer on connect, which overlaps the
        // backfill; dedupe so the chart does not double-plot the overlap.
        if (seenIds.current.has(r.reading_id)) return;
        seenIds.current.add(r.reading_id);
        setLive((prev) => [...prev, r].slice(-limit));
      } catch {
        // A malformed frame should drop that frame, not kill the stream.
      }
    };

    es.onerror = () => {
      // EventSource reconnects on its own; flipping this back to false restores
      // polling meanwhile, so the chart keeps updating either way.
      setStreaming(false);
    };

    return () => es.close();
  }, [incubatorId, limit, since]);

  // Merge: backfill first, then anything the stream added that it did not cover.
  const seed = backfill.data ?? [];
  const seedIds = new Set(seed.map((r) => r.reading_id));
  const from = since ? new Date(since).getTime() : null;
  const merged = [...seed, ...live.filter((r) => !seedIds.has(r.reading_id))]
    .filter((r) => from == null || new Date(r.recorded_at).getTime() >= from)
    .slice(-limit);

  return {
    data: merged,
    isLoading: backfill.isLoading,
    error: backfill.error,
    /** true while the SSE connection is open — drives the "live" indicator */
    streaming,
  };
}
