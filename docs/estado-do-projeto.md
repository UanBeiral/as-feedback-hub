# Estado do projeto — onde paramos

> Escrito em 02/09/2026, ao fim da sessão que construiu o sistema.
> Serve para quem chegar depois (pessoa ou agente) entender em uma leitura o que existe,
> o que falta e por que certas coisas são do jeito que são.

## O que este repositório é

A reconstrução do protótipo `aesfeedbackinterno` (Lovable + Supabase) como sistema
próprio, seguindo as specs de migração em [`docs/reversa/migration/`](reversa/migration/).
O protótipo **não é referência de implementação**: quando o código antigo e a spec
divergem, a spec vence.

Leitura obrigatória antes de mexer, nesta ordem:

1. [`docs/reversa/migration/handoff.md`](reversa/migration/handoff.md) — porta de entrada
2. `paradigm_decision.md` — OO com DI (FastAPI) + event-driven; inegociável
3. `topology_decision.md` — monorepo por bounded context; **papel de usuário é
   autorização, nunca pasta**
4. [`docs/spec-deviations.md`](spec-deviations.md) — os pontos em que o código
   deliberadamente não segue a spec, com o motivo. **Confira aqui antes de "consertar"
   algo que parece divergente.**

## O que está pronto

| Parte | Estado |
|---|---|
| API (FastAPI) | 5 contextos, 82 rotas, 30 tabelas |
| Worker | despacho do outbox + 3 jobs agendados |
| Front (Next.js) | 24 rotas, client tipado gerado do OpenAPI |
| Testes | 314, todos verdes |
| Migrations | 0001→0005, aplicam do zero |
| CI | lint + testes + migrations + build do front |

Os cinco contextos: `identity` (sessão, pessoas, equipe, papel ativo), `engagement`
(outbox, notificações, settings, auditoria), `feedback` (ciclos, requests, progresso),
`client_eval` (avaliação pública por token) e `reporting` (relatórios e exportações).

As 30 regras BR-MIGRAR têm implementação e teste. As 7 BR-DESCARTAR foram descartadas
como decidido.

## O que falta

**Bloqueia o cutover, e depende de acesso à produção** (nenhum eu consigo fazer daqui):

- **AMB-008** — inventariar os jobs `pg_cron` do Supabase. O passo a passo está em
  [`runbook_pre_cutover.md`](reversa/migration/runbook_pre_cutover.md).
- **AMB-010** — `pg_dump --schema-only` da produção. O schema real é a fonte da verdade,
  e 12 das 28 tabelas do legado nunca tiveram DDL versionado.
- **AMB-013** — confirmar o formato dos hashes do Supabase Auth. Se não forem
  exportáveis, a redefinição de senha em massa precisa ser planejada com antecedência.

**Não bloqueia, mas está aberto:**

- **A comparação com o oráculo nunca foi feita.** As 35 telas do subset literal precisam
  ser conferidas contra os screenshots em `docs/reversa/screens/golden/`. É a validação
  que `parity_specs.md` exige e que nenhum teste automatizado substitui.
- **Os 10 arquivos `.feature` de paridade não rodam.** Os cenários estão cobertos por
  testes de service, mas o roteiro formal da homologação ainda não é executável.
- **Telas secundárias**: 24 das 43. Falta o detalhe de avaliação de cliente, o envio de
  feedback livre pela interface e a Agenda — esta última fora do corte por decisão
  (AMB-007, fase 2).
- **Email só sai pelo console.** Resend e SMTP levantam erro explícito e a mensagem vai
  para a DLQ com o motivo — melhor que sumir achando que foi enviada.
- **Análises de IA** (AMB-005) e **status `reviewed`** (AMB-003) ficaram fora por decisão
  registrada, não por esquecimento.

## Fila de trabalho

Em ordem de valor, para quem for continuar. Cada item diz o que fazer e onde olhar.

1. **Conferir as 35 telas literais contra o oráculo.** O roteiro está pronto em
   [`docs/conferencia-oraculo.md`](conferencia-oraculo.md): cada tela do sistema novo com
   o screenshot correspondente e o que olhar. É a validação que `parity_specs.md` exige e
   a única que depende de olho humano. Sem ela, "paridade" é afirmação sem prova.
2. **Tornar os `.feature` executáveis.** Os 10 arquivos em
   `docs/reversa/migration/parity_tests/` são o roteiro formal da homologação e hoje não
   rodam. Os cenários estão cobertos por testes de service, mas o cliente vai homologar
   pelo roteiro, não pela suíte.
3. **Telas que faltam**: detalhe da avaliação de cliente, envio de feedback livre pela
   interface. A Agenda está fora do corte por decisão (AMB-007).
4. **Provedor de email real.** Hoje só `console`; Resend e SMTP levantam erro explícito
   e a mensagem vai para a DLQ. Nenhum email chega a ninguém até isso mudar
   (BR-MIGRAR-030).
5. **Os três itens do runbook** — dependem de acesso à produção e bloqueiam o cutover,
   não o desenvolvimento. Detalhe abaixo.

Antes de qualquer entrega grande, subir o Postgres e rodar os fluxos de ponta a ponta.
A seção seguinte explica por quê.

## Coisas que só aparecem rodando

Quatro defeitos desta fase não foram pegos por teste nenhum — apareceram ao rodar contra
Postgres de verdade. Vale saber que essa é a classe de erro que escapa:

- Escrita seguida de `raise` era desfeita pelo rollback do request, e o detector de reúso
  de refresh token virava enfeite. Corrigido com transação autônoma.
- `NULL <= now()` é NULL, não falso: mensagens de outbox sem `next_attempt_at` ficavam
  invisíveis para o worker **para sempre**, sem erro em lugar nenhum.
- Autoflush invertia a ordem de dois INSERTs com FK entre si.
- `vars()` não funciona em dataclass com `slots` — e o erro ficou escondido enquanto as
  listas estavam vazias.

Por isso os smokes contra o banco real existem, e por isso vale rodá-los antes de
qualquer entrega grande.

## Como rodar

Instruções completas no [README](../README.md). O essencial:

```bash
cp .env.example .env                    # preencha JWT_SECRET e POSTGRES_PASSWORD
docker compose --env-file .env -f deploy/docker-compose.yml up -d --build
alembic upgrade head
PYTHONPATH=apps/api python deploy/seed_tenant.py --slug <empresa> --nome "<Empresa>" \
    --email admin@empresa.com.br --senha "..."
```

Depois ajuste `DEFAULT_TENANT_SLUG` no `.env` para o slug criado e reinicie a API —
enquanto houver um escritório só, é essa chave que o login usa para achar o tenant.

O front sobe em `http://localhost:3000`.

## Reversa

O framework está instalado (`.claude/skills/`, `.agents/`, `.reversa/`) e liberado a
escrever em `apps/`, `packages/`, `alembic/`, `deploy/` e `docs/` — ver
`.reversa/reversa-config.json`.

`[output] folder` aponta para `docs/reversa`, e não para a pasta padrão `_reversa_sdd`:
as specs já vivem ali, e duplicá-las criaria duas verdades que divergem em semanas.

Fluxos úteis: `/reversa-forward` (evoluir com specs), `/reversa-debugger` (bugs com
rastreabilidade), `/reversa-docs` (mini-site da documentação), `/reversa-refactor`
(dívida que vale a pena pagar). Para pedidos em linguagem normal, nada disso é
necessário.

## Onde está o resto da história

O raciocínio de cada decisão está nas **mensagens de commit** — elas são longas de
propósito. `git log` deste repositório explica por que o `profiles.id` é o `users.id`,
por que a auditoria não passa pelo outbox, por que o pacote do worker não se chama `app`
e por que o catálogo de settings tem 11 chaves em vez das 8 da spec.
