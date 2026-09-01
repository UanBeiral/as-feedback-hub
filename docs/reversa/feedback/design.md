# Unidade: Feedback Interno — Design Técnico

## Interface

| Símbolo | Assinatura | Retorno | Observação |
|---------|-----------|---------|------------|
| `openCycle` | `(cycle: any)` | `number` | Transiciona ciclo e dispara geração de requests. 🟢 |
| `generateFeedbackRequestsForMember` | `(newMemberId: string)` | `Promise<void>` | Cria requests conforme permissões. 🟢 |
| `ensureReversePeerPermission` | `(reviewerId, revieweeId, cycleId)` | `Promise<void>` | Garante relação inversa. 🟢 |

## Fluxo Principal

1. Administrador configura ciclo, formulário e permissões. 🟢
2. A abertura valida a janela/frequência e busca pares ativos. 🟢
3. Requests são criados por ciclo, giver e receiver. 🟢
4. Avaliadores salvam rascunho ou enviam respostas. 🟢
5. Dashboards agregam estados e taxa de conclusão. 🟢

## Fluxos Alternativos

- Permissão peer cria também a relação reversa. 🟢
- Request cancelado/abdicado é excluído do progresso. 🟢
- Erro de persistência mantém o estado anterior e informa falha. 🟢
- Contrato de deduplicação server-side é lacuna. 🔴

## Dependências

- Supabase Auth/Postgres, React Query, formulários e componentes de dashboard. 🟢
- `feedback_cycles`, `feedback_permissions`, `feedback_requests`, `feedback_answers`, `feedback_forms`. 🟢

## Decisões de Design Identificadas

| Decisão | Evidência | Confiança |
|---------|-----------|-----------|
| Persistir ciclo e requests no Supabase. | `AdminCiclos.tsx`, `generateFeedbackRequests.ts` | 🟢 |
| Calcular progresso no cliente. | `Dashboard.tsx` | 🟢 |
| Manter relação peer bidirecional. | `AdminPermissoes.tsx` | 🟢 |

## Estado Interno

Estados de ciclo e request persistidos no banco; formulário mantém rascunho/respostas no cliente até mutação. 🟢

## Observabilidade

Auditoria e notificações são efeitos auxiliares; logs estruturados não foram identificados. 🟡

## Riscos e Lacunas

- 🔴 RLS, Edge Functions e constraints de unicidade precisam ser confirmados.
- 🟡 Concorrência de abertura de ciclos depende de regra no cliente.

## Validação humana — 2026-08-25

- 🟢 A unicidade de permissões precisa considerar `cycle_id`; permissões específicas do ciclo têm precedência sobre as globais.
- 🟡 O modelo possui pares redundantes (`giver_id`/`receiver_id` e `reviewer_id`/`reviewee_id`), e um par canônico deve ser escolhido antes de consolidar constraints.
- 🔴 A atomicidade quando dois usuários abrem/geram o mesmo ciclo ainda não foi confirmada.
