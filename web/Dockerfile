# syntax=docker/dockerfile:1
# The browser interface (Next.js, standalone output). It forwards /api to the Python API container.
# Next.js reads the API address when it BUILDS (the forwarding rule is baked in), so it is a build
# argument here, not a run-time variable. Build from the web/ directory:
#   docker build -t sixhats-web --build-arg SIXHATS_API_URL=http://api:8000 web

FROM node:22-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

FROM node:22-slim AS build
WORKDIR /app
ARG SIXHATS_API_URL=http://api:8000
ENV SIXHATS_API_URL=${SIXHATS_API_URL} NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:22-slim
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0 PORT=3000
COPY --from=build --chown=root:root /app/.next/standalone ./
COPY --from=build --chown=root:root /app/.next/static ./.next/static
USER node
EXPOSE 3000
CMD ["node", "server.js"]
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
  CMD ["node", "-e", "fetch('http://127.0.0.1:3000/').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"]
