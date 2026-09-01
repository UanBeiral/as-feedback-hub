---
schemaVersion: 1
generatedAt: 2026-08-28T02:30:00Z
reversa:
  version: "1.2.60"
kind: parity_specs
producedBy: inspector
hash: "sha256:0221ed08538adececebd92fa7579e47bf79595eb0d260bbaaa33ca65e3a7b014"
---

# Parity Specs

> Como provar que o sistema novo (Next.js + FastAPI + Postgres/Redis) é comportamentalmente equivalente ao legado (SPA + Supabase) nos pontos onde isso importa.
> Estes são specs de paridade, não testes executáveis: o agente de codificação traduz os `.feature` para o framework de teste do projeto novo (pytest + Playwright sugeridos).

## Estratégia geral

| Modo de validação | Selecionado | Aplicação neste projeto |
|---|---|---|
| Shadow mode | ❌ | inviável: legado não tem camada de API interceptável (cliente → banco direto) |
| Characterization tests | ✅ | suíte derivada das regras 🟢 de `target_business_rules.md` e das máquinas de estado (não há `characterization_specs/` no legado — lacuna sinalizada abaixo) |
| Contract tests | ✅ | contrato OpenAPI da API nova + contrato de tela (subset modernizado) |
| Data parity | ✅ | contagens/checksums por tabela pós-migração (`data_migration_plan.md` § Validação) |
| Golden file comparison | ✅ | subset literal (35 telas) contra os screenshots do Visor, dentro das regras do `golden/manifest.yaml` |

**Lacuna sinalizada**: o legado não possui `characterization_specs/` nem suíte de testes confiável; os cenários foram derivados de `target_business_rules.md`, `state-machines.md` e `code-analysis.md`. Divergências descobertas na homologação devem retroalimentar estes specs.

## Critérios de paridade aceita

- **Métrica primária**: 100% dos cenários `@critico` passando + zero divergência funcional reportada pelo Validador nos fluxos assistidos da homologação comparativa.
- **Janela de observação**: período de homologação (Parallel Run limitado — `migration_strategy.md` § Fases 4) + 2 semanas pós-cutover de monitoramento (`cutover_plan.md` § Pós-corte).
- **Critério de bloqueio do cutover**: qualquer cenário `@critico` falho, qualquer violação de isolamento de tenant (`@isolamento`), ou validação de dados (contagens/checksums) divergente sem justificativa de quarentena.

## Cobertura adaptada ao paradigma

Transição: **procedural (client-centric) → OO com DI + jobs assíncronos**. Dimensões adicionais obrigatórias (não basta equivalência funcional ingênua):

1. **Invariantes em aggregates** (`procedural → OO`): as regras que no legado eram efeitos de tela precisam falhar **na API**, não na UI — cada invariante tem cenário negativo chamando o endpoint diretamente (bypass de UI).
2. **Idempotência e consistência eventual** (`síncrono → fila/worker` nos efeitos auxiliares): outbox com chave de idempotência; segunda entrega não duplica notificação; falha do worker não desfaz operação principal.
3. **Autorização explícita** (RLS → guards): matriz papel × recurso de `permissions.md` coberta por cenários deny-by-default; parâmetros de URL nunca ampliam escopo.
4. **Isolamento multi-tenant** (novo): nenhum dado de um tenant alcançável por sessão de outro — cobertura obrigatória antes do 2º tenant (R-09).

## Paridade de telas (modo híbrido)

- **Subset literal (35 telas)**: golden file comparison contra os screenshots do Visor referenciados em `_reversa_sdd/screens/golden/manifest.yaml`. Os golden do sistema novo ainda não foram capturados (manifest lista o comando Playwright sugerido) — **até a captura, a validação visual é manual**, guiada pelos screenshots do legado. Cenários em `parity_tests/screens/01-subset-literal.feature` (`@paridade-visual`).
- **Subset modernizado (8 telas)**: contract test de tela — hierarquia de componentes, eventos, conteúdo textual e os 4 estados de `target_screens.md`. Sem comparação byte-a-byte. Cenários em `parity_tests/screens/02-subset-modernizado.feature`.

## Exceções (deviations aprovadas propagadas)

| Deviation | Efeito na paridade |
|---|---|
| DEV-001 (API em vez de supabase.from) | paridade avaliada no comportamento renderizado, nunca no tráfego de rede |
| DEV-002 (exportações assíncronas) | fluxos de PDF/XLSX comparam **conteúdo do arquivo final**, não o tempo/mecanismo de entrega; a UI de "gerando relatório" é divergência aceita |
| DEV-003/006 (tokens em vez de hex) | comparação visual tolera diferença de fonte do valor (token vs literal) desde que a cor renderizada seja equivalente |
| DEV-004 (4 estados no subset modernizado) | estados novos não contam como divergência |
| DEV-005 (rotas duplicadas removidas) | rota canônica única é o esperado; a duplicata do legado não é paridade exigida |
| DEV-007 (auth própria) | mensagens de erro de autenticação podem divergir do texto do provedor Supabase; fluxo e resultado devem ser equivalentes |
| DEV-008 (tokens derivados) | badges/gradiente comparados após extração dos valores exatos |

## Fluxos críticos cobertos

| # | Arquivo | Fluxo | Origem |
|---|---|---|---|
| 01 | `parity_tests/01-abertura-de-ciclo.feature` | abertura de ciclo e geração de requests | BR-MIGRAR-001/002/010/011 |
| 02 | `parity_tests/02-ciclo-de-vida-do-request.feature` | máquina de estados do request (draft/submit/waive/cancel) | BR-MIGRAR-003/008/012; `state-machines.md` |
| 03 | `parity_tests/03-avaliacao-publica-token.feature` | avaliação pública por token, idempotência e expiração | BR-MIGRAR-019/020/021/022 |
| 04 | `parity_tests/04-progresso-e-metricas.feature` | progresso único do ciclo e engajamento | BR-MIGRAR-009/028 |
| 05 | `parity_tests/05-autorizacao-e-escopo.feature` | deny-by-default, flags, escopo de equipe, isolamento de tenant | BR-MIGRAR-013..017; R-04/R-09 |
| 06 | `parity_tests/06-fechamento-automatico.feature` | fechamento com carência de 3 dias (scheduler) | BR-MIGRAR-005; BR-DESCARTAR-003 |
| 07 | `parity_tests/07-notificacoes-outbox.feature` | outbox, idempotência, falha auxiliar tolerada | BR-MIGRAR-023/024/025 |
| 08 | `parity_tests/08-usuarios-soft-delete.feature` | soft-delete com histórico preservado e sessão revogada | BR-MIGRAR-018 |
| 09 | `parity_tests/screens/01-subset-literal.feature` | paridade visual das 35 telas literais | manifest golden |
| 10 | `parity_tests/screens/02-subset-modernizado.feature` | contrato de tela das 8 modernizadas | `target_screens.md` |
