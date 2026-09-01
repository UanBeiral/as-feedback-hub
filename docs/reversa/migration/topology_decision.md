---
schemaVersion: 1
generatedAt: 2026-08-28T00:00:00Z
reversa:
  version: "1.2.60"
kind: topology_decision
producedBy: designer
hash: "sha256:3facdd7eb14595247cab16de46297e8f5d70643906ff64291232560972f4630e"
---

# Topology Decision

> Decisão consciente sobre como organizar o sistema novo: preservar a topologia do legado, adotar uma topologia moderna ou aplicar um híbrido.
> Este artefato é leitura obrigatória do próprio Designer (para decompor bounded contexts) e do agente de codificação (para criar a árvore de pastas).

## Topologia do legado detectada
- **Padrão organizacional**: monolito SPA package-by-type com sub-organização por papel (pages por papel de usuário), sem fronteiras de domínio
- **Confiança**: 🟢 CONFIRMADO
- **Evidências**:
  - `_reversa_sdd/inventory.md` § Estrutura principal: "pastas por área funcional e por tipo de tela, com roteamento centralizado em `src/App.tsx`" — `pages/` divididas por papel (admin, gestor, coordenador, colaborador), `components/`, `hooks/`, `lib/`, `contexts/` por tipo técnico.
  - `_reversa_sdd/architecture.md` § Riscos: "lógica de agregação e autorização distribuída em páginas e componentes" — não há camada de domínio; a fronteira real é a tela.
  - `_reversa_sdd/domain.md` + units: a mesma regra de progresso (excluir `cancelled`/`waived`) aparece implementada em gestor, coordenador e dashboard — duplicação por papel, não por domínio.
- **Mapa da árvore legada** (resumido):
  ```
  src/
  ├── App.tsx                  # roteamento central (com rotas duplicadas)
  ├── pages/
  │   ├── admin/  gestor/  coordenador/  colaborador/  public/
  │   └── (páginas globais: Dashboard, etc.)
  ├── components/              # blocos de UI + modais (com lógica de negócio)
  ├── contexts/  hooks/  lib/  # tipo técnico
  ├── integrations/supabase/   # cliente e tipos do banco
  └── supabase/                # migrations e edge functions (fora do src)
  ```

## Diagnóstico estrutural
- **Acoplamento**: alto — UI acoplada ao schema do banco (`supabase.from` massivo, `any`/casts para tabelas fora dos tipos; `architecture.md` § Riscos).
- **Coesão por módulo**: baixa — módulos são papéis de usuário, não domínios; a mesma regra de negócio atravessa 3+ módulos (progresso, pendências, histórico).
- **Módulos órfãos / mortos**: `src/App.css` residual do template Vite (checkpoint Design System); rotas duplicadas de coordenador em `App.tsx`.
- **Camadas redundantes**: overrides `.dark !important` (~270 linhas) compensando cores hardcoded — camada de correção sobre camada quebrada.
- **Violações de fronteira**: componentes de UI fazem query, autorização e mutação diretamente (ex.: geração de requests disparada de `AdminCiclos.tsx`).
- **Mistura de paradigmas/estilos**: predominantemente procedural em componentes; traço event-driven improvisado nas Edge Functions.
- **Avaliação geral**: **problemática** — a organização por papel × tipo técnico é a causa direta da duplicação de regras e do acoplamento ao schema.

## Topologia moderna proposta
- **Padrão**: **monorepo com apps separados (web/api/worker) e backend em DDD leve — package-by-bounded-context com camadas internas (router → service → repository)**; frontend Next.js feature-sliced consumindo contrato OpenAPI.
- **Justificativa**: o paradigma escolhido (OO com DI + workers) pede camadas explícitas; a estratégia Big Bang permite redesign profundo; o domínio já revelou fronteiras naturais nas specs (ciclos/requests, avaliação pública, identidade/permissões, notificações, relatórios) que não coincidem com os papéis de usuário do legado. Organizar por contexto elimina a duplicação por papel: **papel vira autorização, não estrutura de pastas**.
- **Ganhos concretos esperados**:
  - Regra única por domínio: progresso do ciclo calculado num único service, consumido por todos os papéis (elimina a triplicação atual).
  - Testabilidade por contexto: invariantes de ciclo testáveis sem UI e sem banco real (DI + repositories).
  - Multi-tenancy transversal: `tenant_id` aplicado na camada core, impossível de esquecer por tela.
  - Onboarding: a árvore espelha o domínio documentado em `_reversa_sdd/`, não a navegação.
- **Custo / risco**:
  - Curva de aprendizado de DDD leve + DI disciplinada (mitigada pelo esqueleto de referência da fase Fundação — R-06).
  - Cerimônia adicional em contextos pequenos (mitigada: contextos de leitura pura, como relatórios, podem ter camada de service fina — decisão AMB-004-like documentada por contexto).
- **Esboço da árvore proposta**:
  ```
  repo/
  ├── apps/
  │   ├── web/                     # Next.js (App Router), feature-sliced
  │   │   └── src/features/        # auth, cycles, public-eval, team, reports, admin...
  │   ├── api/                     # FastAPI
  │   │   └── app/
  │   │       ├── core/            # config, db, DI, security, tenancy (middleware)
  │   │       ├── contexts/
  │   │       │   ├── identity/    # auth, perfis, papéis, flags, tenants
  │   │       │   ├── feedback/    # ciclos, permissões, requests, formulários, respostas
  │   │       │   ├── client_eval/ # avaliação pública, tokens, formulários de cliente
  │   │       │   ├── engagement/  # notificações, auditoria, settings do tenant
  │   │       │   └── reporting/   # relatórios, exportações, engajamento
  │   │       │   └── <ctx>/{router,service,repository,models,schemas}.py
  │   │       └── main.py
  │   └── worker/                  # consumidores de fila + scheduler (mesmos contexts via import)
  ├── packages/
  │   └── design-tokens/           # tokens extraídos do design system (sem as 657 cores hardcoded)
  └── deploy/                      # docker-compose, nginx, scripts de migração de dados
  ```

## Opções apresentadas ao usuário
1. **Preservar topologia legada** (conservador)
   - Consequências: reproduzir pastas por papel × tipo no Next.js/FastAPI manteria o mapa mental do protótipo, mas perpetuaria a triplicação de regras por papel e contradiria o paradigma já aprovado (a lógica precisaria continuar espalhada). Dado que o código legado será descartado, preservar a topologia preserva apenas o defeito estrutural.
2. **Adotar topologia moderna proposta** (transformacional)
   - Consequências: rompe com o débito estrutural; árvore nova espelha o domínio; exige disciplina de camadas; máxima aderência ao paradigma e ao multi-tenant.
3. **Híbrido** (equilibrado)
   - Consequências: backend por bounded context (moderno), frontend preservando a organização por papel do legado (`web/src/pages/{admin,gestor,...}`). Reduz o salto mental na UI — as telas continuam mapeadas 1:1 com o que o Visor documentou — ao custo de duplicar componentes entre papéis que compartilham telas (histórico, dashboards de cliente).

## Decisão do usuário
- **Escolha**: 2 — Adotar topologia moderna proposta
- **Justificativa do usuário**: recomendação do Designer aceita (resposta "2"); coerente com o paradigma transformacional e o objetivo multi-tenant já aprovados.
- **Decidido em**: 2026-08-28

## Mapeamento legado → novo
| Módulo / pasta legada | Bounded context novo | Tipo | Observações |
|---|---|---|---|
| `auth` (unit) + perfis/flags de `admin` | `identity` | fundido | sessão, papéis, flags e tenancy são um único domínio de identidade |
| `feedback` (unit) + ciclos/permissões de `admin` | `feedback` | fundido | ciclo, permissões e requests falham juntos (invariantes comuns) |
| `public` (unit) + solicitação de avaliação de `colaborador`/`gestor` | `client_eval` | fundido | todo o ciclo de vida da avaliação externa num contexto |
| `notifications` + `company-settings` (units) + auditoria de `admin` | `engagement` | fundido | efeitos auxiliares e configuração do tenant compartilham infraestrutura (fila, key/value) |
| `reports` (unit) + relatórios de `admin`/`colaborador` | `reporting` | fundido | leitura agregada sobre os outros contextos; camada fina |
| `gestor`, `coordenador`, `colaborador` (units de papel) | (dissolvidos) | dividido | papéis viram autorização + telas; as regras que continham já foram absorvidas pelos contextos acima |
| `admin` (unit de papel) | (dissolvido) | dividido | idem: cada capacidade administrativa pertence ao contexto do domínio que administra |
| Edge Functions / pg_cron / RLS | `worker` + guards da API | removido/substituído | ver `discard_log.md` BR-DESCARTAR-001..004 |
| `integrations/supabase` | (descartado) | removido | substituído por repositories + contrato OpenAPI |

## Implicações pendentes para próximos passos do Designer
| Etapa do Designer | Implicação | Como honrar |
|---|---|---|
| Bounded contexts | Papéis não são contextos | agrupar regras por invariante (ciclos/requests juntos), nunca por papel de usuário |
| target_architecture | Worker compartilha domínio com a API | worker importa os mesmos contexts; jobs são casos de uso, não código paralelo |
| target_domain_model | Regras BR-MIGRAR-001..030 têm dono | cada regra mapeada a um aggregate/service de um único contexto |
| target_data_model | Multi-tenant estrutural | `tenant_id` NOT NULL + FK em toda tabela de domínio; contexto `identity` é dono da tabela `tenants` |

## Notas
- A árvore proposta assume um único repositório e um único deploy (Docker Compose na VPS) — adequado ao tamanho do time; a separação por contexto é lógica, não microsserviços.
- O frontend feature-sliced deve consumir tipos gerados do OpenAPI (`packages/` opcional para o client gerado), nunca redefinir modelos à mão.
