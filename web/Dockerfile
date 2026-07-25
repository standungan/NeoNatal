# Next.js dashboard — production image for a self-hosted VPS.
# Three stages so the runtime image carries only Next's `standalone` bundle:
# no npm, no full node_modules, no source.

FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
# No build args: API_BASE_URL is read at *runtime* by lib/config.ts (server-only),
# so the image is environment-agnostic and the backend need not exist to build.
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN addgroup -g 1001 -S nodejs && adduser -u 1001 -S nextjs -G nodejs

# `output: "standalone"` deliberately omits public/ and .next/static — it assumes
# a CDN serves them. There is no CDN here, so copy them in and server.js picks
# them up automatically.
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
