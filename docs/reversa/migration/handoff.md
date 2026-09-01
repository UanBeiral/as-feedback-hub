---
schemaVersion: 1
generatedAt: 2026-08-28T02:45:00Z
reversa:
  version: "1.2.60"
kind: handoff
producedBy: orchestrator
hash: "sha256:dc1585ea447fa9d7e4d05bdbfd913f38eab89ea824363b5bf1f1e90260cec699"
---

# Handoff para o Agente de Codificação

> Este documento é a porta de entrada para o agente de codificação (Claude Code, Codex, Cursor, etc.) que vai escrever o sistema novo a partir das specs.
> Projeto: **A&S Feedback Hub** — reconstrução como SaaS multi-tenant (Next.js + FastAPI + PostgreSQL + Redis + workers, em VPS própria com Docker/Nginx).

## ⚠️ Leitura obrigatória primeiro

1. **`paradigm_decision.md`** — inegociável. Paradigma alvo: **OO com DI (FastAPI) + event-driven para jobs (Redis/workers)**, apetite `transformational`. Molda toda a codificação.
2. **`topology_decision.md`** — inegociável. Topologia: **moderna (opção 2)** — monorepo web/api/worker, backend por bounded context (`identity`, `feedback`, `client_eval`, `engagement`, `reporting`). **Papel de usuário é autorização, nunca pasta.**
3. **`screen_modernization_decision.md`** — inegociável. Modo de telas: **híbrido** — 35 telas literais (oráculo: screenshots do Visor) + 8 modernizadas (4 estados declarados).

## Ordem de leitura recomendada

1. `paradigm_decision.md`
2. `topology_decision.md`
3. `screen_modernization_decision.md`
4. `migration_brief.md`
5. `target_business_rules.md` (30 regras MIGRAR com rastreabilidade)
6. `migration_strategy.md` (Big Bang + homologação comparativa — confirmada pelo usuário)
7. `target_architecture.md` (AD-01..AD-10)
8. `target_domain_model.md` (16 aggregates; mapa BR→código)
9. `target_data_model.md` (29 tabelas, DDL núcleo)
10. `data_migration_plan.md` (Supabase → Postgres próprio, tenant único)
11. `target_screens.md` (43 telas)
12. `parity_specs.md` + `parity_tests/` (10 arquivos `.feature`)
13. `screen_deviation_log.md` (8 deviations, todas aprovadas)
14. `risk_register.md` (11 riscos, 6 críticos) + `cutover_plan.md`
15. `discard_log.md` (consultivo)
16. `ambiguity_log.md` (consultivo)

## Lista de artefatos produzidos

| Artefato | Produzido por | Status |
|---|---|---|
| migration_brief.md | orchestrator | criado |
| paradigm_decision.md | paradigm_advisor | criado |
| target_business_rules.md | curator | criado (7 decisões humanas resolvidas) |
| discard_log.md | curator | criado |
| migration_strategy.md | strategist | criado (estratégia confirmada) |
| risk_register.md | strategist | criado |
| cutover_plan.md | strategist | criado |
| topology_decision.md | designer (Fase 1) | criado (aprovado: opção 2) |
| target_architecture.md | designer | criado (aprovado) |
| target_domain_model.md | designer | criado |
| target_data_model.md | designer | criado |
| data_migration_plan.md | designer | criado |
| screen_modernization_decision.md | screen_translator (Fase 1) | criado (aprovado: híbrido) |
| target_screens.md | screen_translator | criado (43 telas) |
| screen_deviation_log.md | screen_translator | criado (8 aprovadas, 0 pendentes) |
| _reversa_sdd/screens/inventory.json | screen_translator | criado (45 telas, divergência 0%) |
| _reversa_sdd/screens/golden/manifest.yaml | screen_translator | criado (35 referências) |
| parity_specs.md | inspector | criado |
| parity_tests/*.feature | inspector | 10 arquivos |
| ambiguity_log.md | orchestrator | consolidado (0 pendentes, 7 resolvidos, 6 referidos) |

## Bloqueadores para começar a implementação

**Nenhum bloqueador de decisão.** Todos os itens do `ambiguity_log.md` estão resolvidos ou referidos à codificação. Atenção especial aos referidos que devem ser executados **cedo** (não no fim):

- **AMB-013 / R-07**: verificar exportabilidade dos hashes bcrypt do Supabase Auth **na fase de fundação** — se não forem exportáveis, o fluxo de redefinição em massa precisa ser planejado com antecedência.
- **AMB-010 / R-01**: `pg_dump --schema-only` do banco de produção como fonte da verdade do schema legado, antes de escrever os scripts de migração.
- **AMB-008 / R-08**: inventariar os jobs `pg_cron` de produção antes do design final dos jobs do worker.

## Próximos passos para o agente de codificação

1. **Internalizar as 3 decisões inegociáveis** (paradigma, topologia, modo de telas) — acima.
2. **Configurar o repositório novo** com a árvore de `target_architecture.md § Honra à topologia escolhida` e o Docker Compose de `deploy/` (Nginx TLS, web, api, Postgres, Redis, worker).
3. **Fase Fundação**: `core/` (config, db, security, tenancy, DI), Alembic com a migration inicial multi-tenant (`tenants` primeiro, `tenant_id` NOT NULL em tudo), auth própria (JWT + refresh — AD-03), esqueleto de um contexto de referência revisado antes de escalar (R-06).
4. **Implementar bottom-up por contexto**, na ordem de dependência: `identity` → `engagement` (settings/outbox) → `feedback` → `client_eval` → `reporting`. Infraestrutura → dados → domínio → aplicação → bordas.
5. **Implementar as telas** consumindo `target_screens.md`: subset literal contra os screenshots (manifest); subset modernizado com os 4 estados. Client OpenAPI gerado — nunca modelos redefinidos à mão (AD-08).
6. **Escrever os testes desde o início** a partir de `parity_specs.md` e `parity_tests/*.feature` — cenários `@critico` e `@isolamento` são bloqueadores de cutover. Honrar § Exceções (deviations aprovadas).
7. **Validar cada componente** contra `target_architecture.md § Honra ao paradigma` e `§ Honra à topologia`.
8. **Migração de dados**: `data_migration_plan.md` (scripts idempotentes em `deploy/migrate/`, quarentena `_migration_rejects`, ensaio ≥2x em staging).
9. **Homologação comparativa** com o cliente (Parallel Run limitado): parity specs como roteiro; demonstrar explicitamente a DEV-002 (exportações assíncronas).
10. **Cutover**: `cutover_plan.md` — pré-requisitos, janela de 8h, go/no-go, rollback por DNS com Supabase congelado 30 dias.

## Itens auto-decididos (apenas se executado em --auto)

Pipeline executado em modo interativo, nenhum item auto-decidido. Todas as 13 decisões humanas foram tomadas pelo usuário (Uan) em 2026-08-28: paradigma (opção 1), 7 itens do Curator, estratégia (opção 1), topologia (opção 2), arquitetura (aprovada), modo de telas (híbrido) e 8 deviations (aprovadas).

## Notas finais

- O código legado **não é referência de implementação** — só as specs. Quando uma spec conflitar com o código legado, a spec vence; se a dúvida persistir, os artefatos de `_reversa_sdd/` (requirements por unit, `domain.md`, `permissions.md`) são a fonte.
- Escopo do primeiro corte exclui: análises de IA (AMB-005), Google Calendar/agenda conectada (AMB-007), status `reviewed` (AMB-003), transições não confirmadas de `team_requests` (AMB-004 — retornam 409).
- Fluxo público espontâneo: implementar atrás de flag por tenant, desabilitado por default (AMB-002).
- LGPD: default conservador no schema (anonimização por design, exportação restrita) + formalização com o cliente antes da homologação (AMB-001 / R-10).
- Métrica de sucesso do projeto: **homologação aprovada pelo cliente** — paridade percebida nos fluxos críticos vale mais que qualquer métrica interna.
