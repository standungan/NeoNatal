import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Emits .next/standalone — a self-contained server with a minimal traced
  // node_modules, so the Docker runtime stage needs no install step.
  output: "standalone",

  // These used to live in vercel.json. On a VPS nothing else applies them, and
  // keeping them in Next means they survive a change of reverse proxy.
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
        ],
      },
      {
        // Authenticated payloads pass through here — never let a proxy or the
        // browser cache them.
        source: "/api/:path*",
        headers: [{ key: "Cache-Control", value: "no-store" }],
      },
    ];
  },
};

export default nextConfig;
