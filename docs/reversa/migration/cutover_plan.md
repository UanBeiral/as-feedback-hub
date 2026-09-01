---
schemaVersion: 1
generatedAt: 2026-08-28T00:00:00Z
reversa:
  version: "1.2.60"
kind: cutover_plan
producedBy: strategist
hash: "sha256:d5c4cb7015d5362fd7fd4cac15d7a933a7e57d5fecbc25caff38cbe546bd49f7"
---

# Cutover Plan

> Plano de corte para a estratégia recomendada (Big Bang com homologação comparativa). Se o usuário escolher outra estratégia, este plano é regenerado.
> Owners usam papéis: **Executor** (Uan), **Validador** (cliente do projeto).

## Pré-requisitos (go/no-go depende de todos)

1. ✅ Homologação comparativa aprovada pelo cliente (parity specs do Inspector todas verdes).
2. ✅ Ensaio da migração de dados executado ≥2 vezes em staging, com validação de contagens/checksums por tabela (R-01).
3. ✅ Inventário dos jobs `pg_cron` de produção extraído e mapeado para jobs do worker (AMB-008 / R-08).
4. ✅ Estratégia de credenciais definida e testada: hashes exportados ou fluxo de redefinição comunicado (AMB-009 / R-07).
5. ✅ Backup completo do Supabase (dump lógico + export de storage `company-assets`) com restore testado.
6. ✅ VPS provisionada: Docker Compose (Nginx com TLS, Next.js, FastAPI, Postgres, Redis, worker), backups automáticos agendados, DNS preparado com TTL reduzido.
7. ✅ Email transacional validado no domínio novo (DKIM/SPF — R-11).
8. ✅ Política LGPD formalizada com o cliente ou default conservador ratificado (R-10).

## Janela

- **Quando**: fora do horário de uso do cliente (noite/fim de semana — a confirmar com o Validador).
- **Duração estimada**: 2–4 h de execução + 1 h de validação. Janela reservada: 8 h.
- **Congelamento**: protótipo em modo somente-leitura desde o início da janela (revogar permissões de escrita da anon/authenticated keys ou banner de manutenção).

## Passos

| # | Passo | Owner | Duração |
|---|---|---|---|
| 1 | Comunicar início da janela ao Validador; ativar modo manutenção no protótipo | Executor | 10 min |
| 2 | Dump final do Supabase (dados + storage) | Executor | 20 min |
| 3 | Executar script de migração ensaiado (Supabase → Postgres VPS, incluindo atribuição do tenant único) | Executor | 30–60 min |
| 4 | Validar contagens/checksums por tabela contra o dump; validar migração de credenciais | Executor | 30 min |
| 5 | Smoke test roteirizado no sistema novo: login por papel, abertura de ciclo em staging-tenant, submissão pública por token, notificação, relatório PDF | Executor | 30 min |
| 6 | Apontar DNS para a VPS (TTL já reduzido) | Executor | 10 min + propagação |
| 7 | Validação assistida com o Validador nos fluxos críticos reais | Executor + Validador | 30–60 min |
| 8 | **Go/No-Go final** | Executor + Validador | 10 min |
| 9 | (Go) Encerrar manutenção; comunicar usuários; protótipo permanece congelado como rollback quente | Executor | 10 min |

## Rollback

- **Gatilho**: falha em qualquer validação dos passos 4, 5 ou 7 sem correção viável dentro da janela.
- **Procedimento**: reverter DNS para o Vercel; reativar escrita no Supabase; comunicar o Validador. O protótipo não foi alterado — rollback é apenas roteamento (< 30 min + propagação DNS).
- **Dados**: nenhuma escrita ocorre no sistema novo antes do go (janela em manutenção), portanto não há dados a reconciliar no rollback.
- **Validade do rollback quente**: 30 dias pós-corte com o Supabase congelado em somente-leitura; depois, decomissionar (export final arquivado).

## Critérios de Go/No-Go (passo 8)

| Critério | Go exige |
|---|---|
| Integridade dos dados | 100% das tabelas com contagens/checksums validados |
| Autenticação | Login funcional para os 4 papéis + admin do tenant |
| Fluxos críticos | Ciclo, requests, submissão de feedback, avaliação pública por token operando |
| Autorização | Testes de negar-por-padrão passando; nenhum acesso cruzado observado |
| Jobs | Worker processando fila; job de fechamento agendado |
| Validador | Aprovação explícita do cliente nos fluxos assistidos |

## Pós-corte (primeiras 2 semanas)

- Monitorar: fila (jobs falhos/DLQ), erros HTTP da API, ciclos que não fecham, tokens que não expiram (R-08).
- Revisar auditoria de acessos (R-04).
- Retrospectiva e desbloqueio da fase 2 (IA, Google Calendar — AMB-005/007).
