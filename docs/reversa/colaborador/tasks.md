# Unidade: Colaborador — Tarefas de Implementação

## Pré-requisitos

- [ ] Disponibilizar Supabase, React Query, flags de `profiles` e componentes compartilhados.
- [ ] Confirmar RLS para avaliações e respostas. 🔴

## Tarefas

- [ ] T-01, Implementar rota protegida e carregamento do perfil. Origem: `src/App.tsx`, `src/components/ProtectedRoute.tsx`. Pronto quando sessão, papel e flags forem carregados corretamente. Confiança: 🟢.
- [ ] T-02, Implementar consulta de perfis ativos e `client_feedbacks`. Origem: `src/pages/colaborador/ColaboradorAvaliacoesCliente.tsx`. Pronto quando apenas perfis ativos puderem ser selecionados. Confiança: 🟢.
- [ ] T-03, Implementar filtros, status agregados e máscara de WhatsApp. Origem: `ColaboradorAvaliacoesCliente.tsx`. Pronto quando filtros por pessoa, cliente, telefone, status e datas alterarem a lista e contagens. Confiança: 🟢.
- [ ] T-04, Integrar solicitação de avaliação pelo modal compartilhado. Origem: `ColaboradorAvaliacoesCliente.tsx`, `RequestClientFeedbackModal`. Pronto quando uma solicitação válida atualizar a listagem. Confiança: 🟡.
- [ ] T-05, Implementar controle de respostas por `can_view_feedback_answers`. Origem: `ColaboradorAvaliacoesCliente.tsx`. Pronto quando respostas forem invisíveis sem a flag. Confiança: 🟢.
- [ ] T-06, Implementar dashboard e histórico condicionais às flags. Origem: `ColaboradorDashboardClientes.tsx`, `ColaboradorHistoricoEquipe.tsx`. Pronto quando flags falsas redirecionarem para `/`. Confiança: 🟢.
- [ ] T-07, Implementar relatório CSV filtrado. Origem: `ColaboradorRelatoriosClientes.tsx`. Pronto quando o CSV refletir os filtros e usar `;`. Confiança: 🟢.
- [ ] T-08, Validar RLS, privacidade e autorização entre usuários. Origem: migrations Supabase e páginas do módulo. Pronto quando testes impedirem acesso fora do escopo. Confiança: 🔴.

## Tarefas de Teste

- [ ] TT-01, Testar cada flag isoladamente.
- [ ] TT-02, Testar filtros combinados e estados pendente/respondido/expirado.
- [ ] TT-03, Testar CSV e máscara de telefone.
- [ ] TT-04, Testar falhas de consulta e ausência de dados.
- [ ] TT-05, Testar RLS. 🔴

## Ordem Sugerida

1. T-01 a T-03 para estabelecer escopo e consulta.
2. T-04 a T-07 para recursos condicionais.
3. T-08 e testes antes da liberação.

## Lacunas Pendentes (🔴)

- Confirmar RLS, contrato do modal e limite operacional da exportação.
