---
schemaVersion: 1
generatedAt: 2026-08-28T00:00:00Z
reversa:
  version: "1.2.60"
kind: migration_brief
producedBy: orchestrator
hash: "sha256:f295006aabde7702c1e6b0410ac51f5a8beeef4fc6b9f5a12309971a83a177ec"
---

# Migration Brief

> Documento de critério de migração coletado em entrevista no início do `/reversa-migrate`.
> Consumido pelos seis agentes do Time de Migração. Não pergunta paradigma (responsabilidade do Paradigm Advisor) nem apetite (derivado em `paradigm_decision.md`).

## Objetivo da migração
A stack atual é um **protótipo construído por IA** (Lovable/React SPA + Supabase) cujo propósito foi levantar e validar as regras de negócio junto ao cliente. Cumprido esse papel, o sistema precisa ser reconstruído em uma **stack escalável e multi-tenant**: a previsão é operar como **SaaS com vários clientes** (empresas) acessando a mesma plataforma. Sem a migração, o produto fica preso a uma base de código de qualidade baixa, single-tenant por design e dependente do Supabase.

## Métricas de sucesso
- **Homologação junto ao cliente**: o cliente do projeto valida que o sistema novo reproduz os fluxos de negócio do protótipo (paridade funcional confirmada em homologação).
- Arquitetura multi-tenant operacional: múltiplas empresas isoladas na mesma instância do SaaS. 🟡 INFERIDO do objetivo — alvo numérico de tenants não declarado.
- Sistema rodando na infraestrutura própria (VPS), sem dependência do Supabase. 🟡 INFERIDO da restrição de Postgres em VPS própria.

## Restrições
- **Prazo**: 🔴 LACUNA — não declarado.
- **Orçamento**: 🔴 LACUNA — não declarado.
- **Técnicas**: banco de dados **PostgreSQL em VPS própria** (sai do Supabase gerenciado; auth, storage e edge functions do Supabase precisam de substitutos na stack alvo).
- **Operacionais**: 🔴 LACUNA — janelas de manutenção e SLA durante a migração não declarados.

## Fatores de risco conhecidos
- **Codificação ruim do legado**: o protótipo foi gerado por IA com qualidade baixa (657 cores hardcoded, ~270 linhas de overrides CSS, types desatualizados, DDL não versionado); o código não serve de referência de implementação, apenas as regras de negócio extraídas nas specs.
- Dependências implícitas do Supabase (RLS, auth, pg_cron, edge functions) precisam ser reimplementadas na nova stack. 🟡 INFERIDO dos artefatos do Data Master e Architect.
- Modelo de dados atual é single-tenant (isolamento por `company_id` parcial); a conversão para multi-tenant real é estrutural. 🟡 INFERIDO do ERD.

## Stakeholders
| Nome / papel | Responsabilidade na migração |
|---|---|
| Uan (dono do projeto) | Decisões técnicas e condução da migração |
| Cliente do projeto | Homologação do sistema novo; precisa ser ouvido e informado |

## Stack alvo
- **Linguagem**: TypeScript (front) + Python (back)
- **Framework**: **Next.js** (front) + **FastAPI** (back)
- **Banco**: **PostgreSQL** em VPS própria
- **Mensageria/Jobs**: **Redis** + **workers** (fila e processamento assíncrono)
- **Infra**: VPS própria com **Docker** e **Nginx** (reverse proxy)
- **Outros componentes relevantes**: cache via Redis; observabilidade 🔴 LACUNA — não declarada.

## Escopo declarado
- **Incluído**: todos os módulos do legado — admin, gestor, coordenador, colaborador, feedback, public, notifications, auth, company-settings, reports.
- **Excluído**: nenhum.

## Notas livres
O valor do legado está nas specs extraídas em `_reversa_sdd/` (regras de negócio, máquinas de estado, permissões, ERD, telas), não no código. A migração é uma **reconstrução** orientada a multi-tenancy, não um port do código existente.
