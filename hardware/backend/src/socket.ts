import { Server } from "socket.io";
import type { Server as HttpServer } from "http";

// Socket.IO dengan room per incubator: dashboard yang buka incubator A hanya
// dapat data incubator A. Frontend kirim event "join" berisi incubator_id.
export function createSocket(httpServer: HttpServer): Server {
  const io = new Server(httpServer, { cors: { origin: "*" } });

  io.on("connection", (socket) => {
    socket.on("join", (incubatorId: unknown) => {
      if (typeof incubatorId === "string" && incubatorId) socket.join(incubatorId);
    });
  });

  return io;
}
