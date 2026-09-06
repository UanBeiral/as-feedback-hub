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

E `docs/estado-do-projeto.md`: o que existe, o que falta e o que só aparece rodando
contra banco de verdade. É a leitura mais curta para entender onde o projeto está.

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

Para **exercitar as telas** — conferir contra o oráculo, demonstrar, ou só ver o sistema
com gente dentro — use o tenant de demonstração em vez do admin solitário acima:

```bash
PYTHONPATH=apps/api python deploy/seed_demo.py --slug demo --senha "Demo!2026"
```

Ele cria nove pessoas nos quatro papéis (com um coordenador e um desligado), um ciclo
aberto com pedidos em todos os estados, avaliações de cliente respondidas e pendentes,
anotações, notificações, comunicados e auditoria — e deixa defeitos de propósito na
matriz de permissões, para a tela de Diagnóstico ter o que diagnosticar. Depois aponte
`DEFAULT_TENANT_SLUG=demo` no `.env` e reinicie a API. `--recriar` refaz do zero.

E o front, em outro terminal:

```bash
cd apps/web && npm install
npm run gen:api      # regenera o client tipado a partir de openapi.json (AD-08)
npm run dev          # http://localhost:3000, com /api indo para a API local
```

O Redis ainda não é necessário: a fila do outbox é o próprio Postgres (polling por
`status='pending'`), como descreve `target_data_model.md`. Suba `redis` quando o worker
existir.

### Email

`EMAIL_PROVIDER` aceita três valores (BR-MIGRAR-030 / R-11):

| valor | o que faz | exige |
|---|---|---|
| `console` | escreve no log e não envia nada | — |
| `resend` | o provedor que o legado já usava | `RESEND_API_KEY` e domínio de `EMAIL_FROM` verificado |
| `smtp` | servidor próprio ou relay | `SMTP_HOST`; STARTTLS obrigatório salvo `SMTP_TLS=false` |

**Configuração incompleta impede o worker de subir**, de propósito: subir e falhar em
cada envio encheria a DLQ em silêncio, e o escritório descobriria por um cliente dizendo
que não recebeu. Falha do provedor é outra coisa — essa é temporária, vai para retry e
termina na DLQ com o motivo à vista.

Para ver os emails em desenvolvimento sem gastar domínio verificado, suba a caixa falsa:

```bash
docker compose --env-file .env -f deploy/docker-compose.yml --profile dev up -d mailpit
# EMAIL_PROVIDER=smtp  SMTP_HOST=mailpit  SMTP_PORT=1025  SMTP_TLS=false
```

A caixa fica em http://localhost:8025. O `--profile dev` existe para ela nunca subir em
produção por acidente.

Antes do corte, valide o provedor de verdade — é o que R-11 pede, e nenhum teste
automatizado alcança, porque em teste o provedor é um dublê:

```bash
PYTHONPATH=apps/api:apps/worker python deploy/testar_email.py voce@empresa.com.br
```

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
