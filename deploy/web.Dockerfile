# Build do Next.js em duas etapas: a imagem final não carrega o toolchain.
FROM node:22-slim AS build

WORKDIR /srv/apps/web

COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY packages/design-tokens /srv/packages/design-tokens
COPY apps/web ./

ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:22-slim AS runtime

WORKDIR /srv/apps/web
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1

COPY --from=build /srv/apps/web/package.json ./package.json
COPY --from=build /srv/apps/web/node_modules ./node_modules
COPY --from=build /srv/apps/web/.next ./.next
COPY --from=build /srv/apps/web/public ./public

# Roda sem privilégio, como a API.
RUN useradd --create-home --uid 10002 web && chown -R web:web /srv
USER web

EXPOSE 3000
CMD ["npm", "run", "start"]
