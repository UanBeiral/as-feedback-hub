---
schemaVersion: 1
generatedAt: 2026-08-28T00:00:00Z
reversa:
  version: "1.2.60"
kind: paradigm_decision
producedBy: paradigm_advisor
hash: "sha256:d760e42463e01ca781bbb0d185144685e5d7a8d665efdc2c9639f063c6370b0b"
---

# Paradigm Decision

> Decisão consciente sobre como tratar a mudança (ou ausência) de paradigma entre o legado e a stack alvo.
> Este artefato é leitura obrigatória primeiro para qualquer agente posterior e para o agente de codificação.

## Paradigma do legado detectado
- **Paradigma principal**: procedural (client-centric: lógica de negócio distribuída em páginas/componentes React, dados como rows sem modelo de domínio)
- **Confiança**: 🟢 CONFIRMADO
- **Evidências**:
  - `_reversa_sdd/architecture.md` § Riscos e dívidas: "a lógica de agregação e autorização está distribuída em páginas e componentes, aumentando o acoplamento ao schema Supabase" — ausência de aggregates ou camada de serviço.
  - `_reversa_sdd/inventory.md` § Banco de dados: "uso massivo de `supabase.from(...)` no frontend" — acesso direto a tabelas a partir da UI, dados tratados como dicts/rows.
  - `_reversa_sdd/domain.md` § Regras de negócio: autorização delegada a RLS do Supabase + flags de UI (🟡 INFERIDO), sem camada de aplicação própria.
- **Variações observadas** (traço secundário, não estrutural):
  - Notificações em background: event-driven embrionário ⚠️ — Edge Functions com `waitUntil`/Promise pendente e jobs `pg_cron` (`_reversa_sdd/domain.md` § Decisões e sinais do histórico; `_reversa_sdd/database/procedures.md`). Periférico ao fluxo principal.

## Stack alvo declarada
- Linguagem: TypeScript (front) + Python (back)
- Framework: Next.js (front) + FastAPI (back), Redis + workers para assíncrono
- Infra: VPS própria com Docker e Nginx; PostgreSQL próprio

## Paradigma natural inferido
- **Paradigma**: OO com DI no backend (FastAPI: services, repositories, dependency injection nativa) + event-driven para jobs (Redis + workers); Next.js como camada de apresentação consumindo API.
- **Justificativa**: FastAPI é construído sobre injeção de dependências (`Depends`) e Pydantic, favorecendo camadas explícitas (router → service → repository) — catálogo: "Python moderno (FastAPI) → OO com DI ou procedural rico". A presença declarada de Redis + workers no brief torna natural mover todo processamento assíncrono (notificações, relatórios, fechamento de ciclos) para filas.
- **Alternativas viáveis**: procedural rico (funções + Pydantic, sem classes de serviço) — menor cerimônia, porém pior para multi-tenancy disciplinada; event-driven pleno (tudo vira evento) — sobre-engenharia para o porte atual do domínio.

## Gap identificado
- **Severidade**: alto
- **Implicações concretas**:
  - **Abertura de ciclo sai da tela e vira aggregate**: "a abertura de um ciclo cria requests a partir das permissões ativas" (`domain.md` 🟢) hoje roda como queries disparadas do cliente. No alvo, `FeedbackCycle` é aggregate no FastAPI que garante invariantes (usuários ativos, carência de 3 dias, período avaliado com extensão manual); o front chama `POST /cycles`.
  - **Autorização deixa de ser RLS + flags de UI e vira camada explícita com tenant**: a matriz RBAC de `permissions.md` depende de RLS nunca comprovada (`confidence-report.md`). No alvo, dependency de autorização no FastAPI com escopo de `tenant_id` em toda query — fundação do multi-tenant.
  - **Notificações e jobs saem de Edge Functions/pg_cron e viram fila Redis + workers**: o histórico registra a fragilidade do `waitUntil` no Deno Deploy (`domain.md` 🟢). No alvo, notificar = enfileirar job; falha vira retry com idempotência; fechamento automático de ciclo (hoje `pg_cron` não versionado — gap do Data Master) vira job agendado do worker.
  - **Acesso a dados deixa de ser `supabase.from(...)` com `any`/casts e vira contrato de API tipado**: `architecture.md` aponta componentes com `any` e casts para tabelas fora dos tipos gerados. No alvo, Pydantic schemas + repositories; Next.js consome contrato OpenAPI; o schema do banco deixa de vazar para a UI.

## Opções apresentadas ao usuário
1. **Adotar paradigma natural da stack** (transformacional)
   - Consequências: reconstrução real (não port); maior esforço inicial; multi-tenancy estrutural desde o dia 1; elimina a dívida do protótipo; as 4 implicações acima adotadas integralmente.
2. **Forçar paradigma similar ao legado** (conservador)
   - Consequências: lógica permanece no cliente Next.js com FastAPI como proxy fino (recriando o padrão Supabase); migração mais rápida; multi-tenant dependente de disciplina em cada query do front; tendência a reproduzir a codificação ruim do protótipo; Redis/workers subutilizados. Contraindica o objetivo do brief.
3. **Híbrido** (equilibrado)
   - Consequências: núcleo crítico (ciclos, requests, permissões, tenancy, avaliação pública por token) no paradigma natural; módulos de leitura (relatórios, históricos, anotações) como CRUD simples; exige disciplina na fronteira.

## Decisão do usuário
- **Escolha**: 1
- **Justificativa do usuário**: o objetivo declarado no brief é sair de um protótipo gerado por IA (codificação ruim) para um SaaS multi-tenant escalável; a opção transformacional é a única alinhada a esse objetivo. (Usuário confirmou com "1", sem justificativa adicional em texto livre.)
- **Decidido em**: 2026-08-28T00:00:00Z

## Apetite derivado
- `derived_appetite`: transformational

## Implicações pendentes para próximos agentes
| Agente | Implicação | Como honrar |
|---|---|---|
| Curator | O código do legado não é referência de implementação; só as regras extraídas valem | Classificar regras de negócio como MIGRAR; descartar padrões estruturais do protótipo (queries no cliente, RLS como única autorização, Edge Functions) registrando no discard_log |
| Strategist | Reconstrução transformacional, não port incremental do código | Avaliar estratégias compatíveis com reconstrução paralela (big bang de código com paridade validada em homologação); planejar migração de dados Supabase→Postgres próprio no cutover |
| Designer | OO com DI + workers; multi-tenancy estrutural | Topologia e arquitetura com camadas router/service/repository, `tenant_id` no modelo de dados desde a raiz, fila Redis para todo assíncrono; substitutos para Supabase Auth e Storage |
| Screen Translator | Front deixa de conter lógica de negócio | Telas Next.js consomem API; nenhuma regra de negócio em componente; tokens do design system extraído podem ser reaproveitados sem as 657 cores hardcoded |
| Inspector | Paridade é de comportamento, não de estrutura | Parity specs verificam regras de negócio (ciclos, requests, avaliação pública) contra a API nova, não contra a implementação antiga |

## Notas
- O apetite `transformational` autoriza os agentes seguintes a propor rupturas estruturais (schema novo multi-tenant, auth própria, fila para tudo assíncrono) desde que as regras de negócio 🟢 de `domain.md` sejam preservadas.
- A avaliação pública por token (`client_feedbacks`) é o único fluxo sem autenticação; no alvo precisa de endpoint público próprio com validação de token e rate limiting — atenção do Designer.
- Métrica de sucesso do brief é homologação com o cliente: paridade funcional percebida importa mais que paridade de tela pixel-perfect.
