---
schemaVersion: 1
generatedAt: 2026-08-28T00:00:00Z
reversa:
  version: "1.2.60"
kind: migration_strategy
producedBy: strategist
hash: "sha256:f85f666973d2c867c2d987cb9b18aede91386d9e783debb99cfdd8e0eeadbd2c"
---

# Migration Strategy

> Avaliação de estratégias de migração com trade-offs explícitos. A decisão final é humana.

## Contexto sintetizado

| Dimensão | Valor | Fonte |
|---|---|---|
| Tamanho do legado | Pequeno-médio: SPA única, 10 módulos funcionais, ~28 tabelas, 12 Edge Functions | `inventory.md`, checkpoint Data Master |
| Integrações externas vivas | Supabase (plataforma inteira), Vercel (deploy), Resend (email), Google Calendar (opcional — adiada, AMB-007) | `architecture.md`, `reports/requirements.md` |
| Produção | Sim — 1 cliente (o cliente do projeto) usando o protótipo | `migration_brief.md` |
| Apetite derivado | `transformational` | `paradigm_decision.md` |
| Gap de paradigma | Alto (procedural client-centric → OO com DI + workers) | `paradigm_decision.md` |
| Prazo / orçamento | 🔴 Indefinidos no brief | `migration_brief.md` |
| Regulação | LGPD (dados sensíveis de feedback; política pendente — AMB-001 resolvida com default conservador) | `target_business_rules.md` |
| Natureza do legado | Protótipo gerado por IA; código sem valor de referência, specs são a fonte | `migration_brief.md`, `paradigm_decision.md` |
| Regras críticas | Ciclos/requests (BR-MIGRAR-001..012), autorização negar-por-padrão (013..018), avaliação pública idempotente (019) | `target_business_rules.md` |

## Estratégias avaliadas

### Descartadas no filtro

- **Strangler Fig**: exigiria rotear gradualmente entre a SPA Supabase e a stack nova. Inviável aqui: o legado não tem camada de API própria para interceptar (o cliente fala direto com o banco), o modelo de dados muda estruturalmente (multi-tenant) e o código não será preservado. Cada "fatia" estrangulada exigiria sincronização bidirecional Supabase ↔ Postgres próprio — custo alto sem benefício, dado que o legado é um protótipo em fim de vida.
- **Branch by Abstraction**: pressupõe evoluir o mesmo codebase por trás de abstrações. O codebase será descartado por decisão do `paradigm_decision.md`; não se aplica.

### Candidata A — Big Bang (reconstrução paralela + cutover único) ← RECOMENDADA

- **Adequação ao apetite**: máxima — o catálogo indica Big Bang para apetite `transformational` em sistemas pequenos; este legado é pequeno e está em semi-decommission (protótipo).
- **Adequação ao gap**: o gap alto é atravessado de uma vez, sem estados intermediários híbridos (que seriam o maior risco: manter dois modelos de autorização e dois bancos sincronizados).
- **Custo**: baixo-médio. **Risco**: alto no cutover, mitigável (ver abaixo). **Tempo**: curto-médio.
- **Prós específicos**:
  - O sistema novo nasce multi-tenant limpo, sem herdar compromissos do schema single-tenant.
  - O protótipo continua operando intocado durante toda a reconstrução — zero risco para o cliente até o dia do corte.
  - Um único evento de migração de dados (Supabase → Postgres próprio), ensaiável quantas vezes for preciso.
- **Contras específicos**:
  - Não entrega valor incremental: o cliente só vê o sistema novo na homologação.
  - O cutover concentra o risco num evento único — exige plano de rollback real.

### Candidata B — Parallel Run (complemento de validação, não estratégia principal)

- **Adequação**: o catálogo manda sinalizar Parallel Run sempre que gap alto + apetite transformacional, para provar paridade das regras críticas.
- **Custo**: alto se rodado por longo período; **aqui, proposto em forma limitada**: período de homologação com os dois sistemas ativos (protótipo em produção + sistema novo com dados migrados em staging), comparando os fluxos críticos — abertura de ciclo, geração de requests, progresso, submissão pública — sobre os mesmos dados.
- **Por que não como estratégia principal**: manter dupla escrita contínua exigiria sincronização entre dois modelos de dados incompatíveis (single vs. multi-tenant); o custo não se justifica para 1 cliente.

## Recomendação

**Big Bang (reconstrução paralela + cutover único), com Parallel Run limitado ao período de homologação.**

Justificativa rastreável:
1. Apetite `transformational` + sistema pequeno → Big Bang permitido pelo catálogo (`paradigm_decision.md` § Apetite; `inventory.md` § tamanho).
2. Legado é protótipo em fim de vida → catálogo: "sistema legado já em decommission → prefira Big Bang" (`migration_brief.md` § Objetivo).
3. Gap alto + transformational → Parallel Run de validação obrigatório sobre as regras críticas (regra do catálogo), materializado como homologação comparativa — que coincide com a métrica de sucesso do brief ("homologação junto ao cliente").
4. Sem estratégia incremental viável: a ausência de camada de API no legado elimina Strangler Fig tecnicamente.

**Nota de sensibilidade ao prazo**: o brief não declara prazo nem orçamento. A recomendação assume que a janela de reconstrução (sem valor entregue ao cliente nesse meio-tempo) é aceitável. Se surgir pressão de prazo, o escopo do primeiro corte já está protegido pelas decisões AMB-005 (IA adiada) e AMB-007 (Calendar adiado) — não recomende reintroduzi-los.

## Fases da estratégia recomendada

1. **Fundação** — repositório novo, Docker Compose (Nginx, Next.js, FastAPI, Postgres, Redis, worker), CI, auth própria, modelo multi-tenant base.
2. **Reconstrução bottom-up** — implementação por domínio na ordem de dependência: auth/tenancy → company-settings → perfis/permissões → ciclos/requests → avaliação pública → notificações → relatórios. (Detalhamento é do Designer/handoff.)
3. **Migração de dados ensaiada** — scripts Supabase → Postgres próprio idempotentes e re-executáveis; inclui extração do inventário `pg_cron` (AMB-008) e das credenciais de auth (AMB-009).
4. **Homologação comparativa (Parallel Run limitado)** — sistema novo em staging com dados reais migrados; cliente valida paridade dos fluxos críticos contra o protótipo; parity specs do Inspector servem de roteiro.
5. **Cutover** — ver `cutover_plan.md`.
6. **Observação pós-corte** — protótipo congelado em somente-leitura como rollback quente por período definido, depois decomissionado.

## Estratégia escolhida pelo usuário

- **Escolha**: **Big Bang (reconstrução paralela + cutover único) com Parallel Run limitado à homologação** — recomendação do Strategist aceita (opção 1)
- **Decisor**: Uan
- **Data**: 2026-08-28
