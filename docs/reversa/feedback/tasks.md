# Unidade: Feedback Interno — Tarefas de Implementação

## Pré-requisitos

- [ ] Schema de ciclos, permissões, requests, formulários e respostas.
- [ ] Confirmar RLS, constraints e Edge Functions. 🔴

## Tarefas

- [ ] T-01, Implementar ciclo e transições. Origem: `src/pages/admin/AdminCiclos.tsx`. Pronto quando estados válidos forem persistidos. Confiança: 🟢.
- [ ] T-02, Implementar geração idempotente de requests. Origem: `src/lib/generateFeedbackRequests.ts`. Pronto quando pares elegíveis receberem exatamente os requests esperados. Confiança: 🟡.
- [ ] T-03, Implementar permissões e reversão peer. Origem: `src/pages/admin/AdminPermissoes.tsx`. Pronto quando a relação inversa for criada/preservada. Confiança: 🟢.
- [ ] T-04, Implementar preenchimento, rascunho e envio de respostas. Origem: páginas de feedback e `feedback_answers`. Pronto quando submitted persistir respostas. Confiança: 🟡.
- [ ] T-05, Implementar métricas e exclusão de estados cancelados/abdicados. Origem: `src/pages/Dashboard.tsx`. Pronto quando percentuais coincidirem com os requests válidos. Confiança: 🟢.
- [ ] T-06, Validar autorização e concorrência no banco. Origem: `supabase/migrations`. Pronto quando testes de isolamento e dupla abertura passarem. Confiança: 🔴.

## Tarefas de Teste

- [ ] TT-01, ciclo draft→open→closed.
- [ ] TT-02, geração idempotente e peer reverso.
- [ ] TT-03, envio, rascunho, cancelamento e abdicação.
- [ ] TT-04, RLS e concorrência. 🔴

## Ordem Sugerida

1. Schema e permissões; 2. ciclos/requests; 3. respostas; 4. métricas; 5. segurança.

## Lacunas Pendentes (🔴)

- Confirmar contratos server-side, constraints e transições permitidas.
