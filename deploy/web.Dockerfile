# Build do Next.js em duas etapas: a imagem final não carrega o toolchain.
FROM node:22-slim AS build

WORKDIR /srv/apps/web

COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY packages/design-tokens /srv/packages/design-tokens
COPY apps/web ./

# O destino do rewrite de /api é resolvido no `next build` e gravado no
# routes-manifest — variável de ambiente em runtime não muda mais nada. Por isso vem
# como build arg: dentro do compose, a API é `http://api:8000`. Em produção com Nginx
# na frente (AD-06) o rewrite nem chega a ser usado, porque /api é interceptado antes.
ARG API_ORIGIN=http://api:8000
ENV API_ORIGIN=${API_ORIGIN}     NEXT_TELEMETRY_DISABLED=1

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
