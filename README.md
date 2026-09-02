# A&S Feedback Hub

SaaS multi-tenant de feedback 360 e avaliação de clientes. Reconstrução do protótipo
Lovable/Supabase como sistema próprio, a partir das specs de migração do Reversa.

## Antes de escrever qualquer linha

Leia, nesta ordem, em `docs/reversa/migration/`:

1. **`handoff.md`** — porta de entrada.
2. **`paradigm_decision.md`** — inegociável. OO com DI (FastAPI) + event-driven para jobs.
3. **`topology_decision.md`** — inegociável. Monorepo, backend por bounded context.
   **Papel de usuário é autorização, nunca pasta.**
4. **`screen_modernization_decision.md`** — inegociável. 35 telas literais + 8 modernizadas.

Depois, `docs/spec-deviations.md`: os pontos em que o código deliberadamente **não**
segue a spec, com o motivo. Antes de "consertar" algo que parece divergente, confira lá.

O código legado **não é referência de implementação**. Quando uma spec conflitar com o
que o protótipo fazia, a spec vence.

## Stack

| Camada | Tecnologia |
|---|---|
| Web | Next.js, feature-sliced, consumindo client gerado do OpenAPI (AD-08) |
| API | FastAPI, routers/services/repositories por bounded context |
| Worker | Consumidores da fila Redis + scheduler dos jobs de ciclo (AD-05) |
| Banco | PostgreSQL, schema multi-tenant, migrations Alembic |
| Fila | Redis, retry exponencial + DLQ (AMB-006) |
| Infra | VPS própria, Docker Compose atrás de Nginx com TLS |

## Estrutura

```
apps/api/app/core/          config, db, security, tenancy, di
apps/api/app/contexts/      identity, feedback, client_eval, engagement, reporting
apps/worker/app/            consumers, scheduler, jobs
apps/web/src/features/      auth, cycles, team, client-eval, reports, admin, notifications
packages/design-tokens/     tokens semânticos (docs/reversa/design-system/)
deploy/                     docker-compose, nginx, scripts de migração de dados
alembic/                    migrations do schema novo
docs/reversa/               specs (fonte da verdade)
```

## Rodando local

```bash
cp .env.example .env                    # preencha JWT_SECRET (32+ caracteres)
pip install -e "apps/api[dev]"

# --env-file .env não é opcional: o compose procura o .env ao lado do arquivo dele
# (deploy/), não na raiz, e sem POSTGRES_PASSWORD ele falha antes de subir nada.
docker compose --env-file .env -f deploy/docker-compose.yml up -d postgres

alembic upgrade head                    # da raiz: é onde vive o alembic.ini
PYTHONPATH=apps/api python deploy/seed_tenant.py     --slug as --nome "A&S" --email admin@exemplo.com --senha "..."

cd apps/api && uvicorn app.main:app --reload
```

E o front, em outro terminal:

```bash
cd apps/web && npm install
npm run gen:api      # regenera o client tipado a partir de openapi.json (AD-08)
npm run dev          # http://localhost:3000, com /api indo para a API local
```

O Redis ainda não é necessário: a fila do outbox é o próprio Postgres (polling por
`status='pending'`), como descreve `target_data_model.md`. Suba `redis` quando o worker
existir.

## Invariantes que o CI protege

- **Isolamento de tenant** (AD-10, R-09): nenhuma query de domínio sem `tenant_id`.
  RLS não é o mecanismo primário — o filtro vive na camada de repositório, com testes
  de isolamento obrigatórios.
- **Autorização deny-by-default** (AD-02, R-04): a cadeia `tenant → papel → flag → escopo`
  nega quando qualquer elo falta.

## Pendências de apuração contra a produção legada

Antes do cutover, três itens do `docs/reversa/migration/runbook_pre_cutover.md`
precisam ser respondidos: inventário `pg_cron` (AMB-008), schema real via `pg_dump`
(AMB-010/011/012) e formato dos hashes do Supabase Auth (AMB-013). Nenhum deles
bloqueia a implementação — só os scripts de migração de dados e o cutover.
