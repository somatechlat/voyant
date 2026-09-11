# syntax=docker/dockerfile:1
# =============================================================================
# Voyant Dashboard — production image
# Stage 1: build the Lit/Vite SPA with Bun.
# Stage 2: serve the static bundle with nginx (reverse-proxies /v1, /mcp, /ws).
# Build context: dashboard/ (see infra/standalone/docker-compose.yml).
# Container port: 80 (mapped to host 45001 in the standalone stack).
# =============================================================================

FROM oven/bun:1 AS build
WORKDIR /app

COPY package.json bun.lock ./
RUN bun install --frozen-lockfile

COPY . .
RUN bun run build

FROM nginx:1.27-alpine

RUN apk add --no-cache curl

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
