# Unidade: Gestor, Design Técnico

## Interface

A unidade é composta por páginas React protegidas, componentes compartilhados e consultas Supabase via React Query. Não expõe API HTTP própria.

| Símbolo | Assinatura | Retorno | Observação |
|---------|-----------|---------|------------|
| `GestorInicio` | `()` | `JSX.Element` | Dashboard de ciclo, equipe, progresso, atrasos e gráficos. |
| `GestorEquipe` | `()` | `JSX.Element` | Lista membros e permite adicionar, remover e solicitar avaliações. |
| `GestorPendentes` | `()` | `JSX.Element` | Lista requests `pending`/`draft`, agrupados por avaliador. |
| `GestorHistorico` | `()` | `JSX.Element` | Histórico de feedbacks internos e de cliente com filtros. |
| `ReminderButton` | `(memberId, memberName, pendingCount, variant?)` | `JSX.Element` | Dispara lembrete para pendências do membro. |

## Fluxo Principal

1. `ProtectedRoute` valida sessão e permite o contexto `gestor`, `admin` ou `rh`.
2. `AuthContext` fornece o perfil ativo; o gestor é identificado por `manager_id` e o papel ativo.
3. `GestorInicio` consulta ciclo aberto, membros, requests, respostas e leituras necessárias.
4. Os dados são filtrados por equipe e agregados em memória por membro, status, prazo e nota.
5. `GestorEquipe` apresenta os membros e permite ações por modais compartilhados.
6. `GestorPendentes` consulta requests pendentes, aplica busca/status e oferece cancelamento com justificativa.
7. `GestorHistorico` consulta feedbacks submetidos e renderiza detalhes e métricas históricas.
8. `AppSidebar` decide a visibilidade de relatórios e agenda com base em `company_settings`.

## Fluxos Alternativos

- **Gestor sem equipe:** o dashboard exibe estado vazio e não calcula métricas de equipe inexistente.
- **Ciclo sem requests:** indicadores usam zero como denominador seguro e exibem taxa sem divisão inválida.
- **Request atrasado:** `due_date` e a função de status visual classificam pendência além da tolerância.
- **Cancelamento:** a mutação altera o status para `cancelled`; erro é exibido sem confirmar sucesso.
- **Adicionar membro:** o fluxo pode exigir aprovação em `TeamRequestsSection`; administradores/gestores podem adicionar diretamente conforme a regra observada.
- **Falha de notificação ou auditoria:** o caminho principal de equipe pode concluir e registrar a falha auxiliar.
- **Relatórios desabilitados:** `gestor_can_access_reports` remove o item da navegação, embora o controle server-side permaneça uma lacuna.

## Dependências

- `src/contexts/AuthContext.tsx`: perfil e papel ativo.
- `src/components/ProtectedRoute.tsx`: proteção da família de rotas.
- `src/integrations/supabase/client.ts`: consultas e mutations.
- `@tanstack/react-query`: carregamento e cache remoto.
- `src/components/TeamRequestsSection.tsx`: aprovações de entrada de membros.
- `src/components/AddMemberModal.tsx` e `RemoveMemberModal.tsx`: ações de equipe.
- `src/components/RequestClientFeedbackModal.tsx`: solicitação de avaliação externa.
- `src/components/ReminderButton.tsx`: lembrete de pendências.
- `src/lib/feedbackStatus.ts`: status visual e tolerância de prazo.
- `src/lib/createAuditLog.ts`: auditoria de ações relevantes.

## Decisões de Design Identificadas

| Decisão | Evidência no código | Confiança |
|---------|-----------|-----------|
| Escopo da equipe é derivado de `manager_id` | `src/pages/gestor/GestorInicio.tsx`, `GestorEquipe.tsx` | 🟢 |
| Métricas são agregadas no cliente | `src/pages/gestor/GestorInicio.tsx` | 🟢 |
| Pendências são separadas de histórico submetido | `src/pages/gestor/GestorPendentes.tsx`, `GestorHistorico.tsx` | 🟢 |
| Status visual considera prazo sem necessariamente alterar status persistido | `src/lib/feedbackStatus.ts` | 🟢 |
| Relatórios do gestor dependem de configuração global | `src/components/layout/AppSidebar.tsx`, `src/pages/admin/AdminConfiguracoes.tsx` | 🟢 |
| RLS restringe dados ao escopo da equipe | não confirmado diretamente nas páginas | 🟡 |

## Estado Interno

- Queries remotas: ciclo aberto, membros, requests, respostas, ciclos históricos e avaliações de clientes.
- Filtros locais: busca, status, ciclo, datas, visibilidade de cancelados e ordenação.
- Estados de mutação: carregando, sucesso e erro para cancelamento, inclusão, remoção e lembretes.
- Estados derivados: total, enviados, pendentes, atrasados, taxa de conclusão, notas e leituras não confirmadas.

## Observabilidade

- Toasts informam sucesso/erro de ações, cancelamentos, lembretes e exportações.
- Auditoria registra ações administrativas de equipe quando o fluxo a invoca.
- Banners destacam ciclo fechado, prazo e feedback não lido.
- Não foi confirmada telemetria central de performance ou métricas do gestor. 🔴

## Riscos e Lacunas

- 🔴 RLS e autorização de dados por equipe precisam ser confirmados nas migrations.
- 🔴 O contrato da notificação de lembrete não foi validado na Edge Function correspondente.
- 🟡 Agregações no cliente podem carregar mais requests que o necessário em equipes grandes.
- 🟡 A configuração global pode ocultar o menu sem impedir acesso direto à rota, caso não exista proteção adicional.
