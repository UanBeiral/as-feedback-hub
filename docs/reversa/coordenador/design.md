# Unidade: Coordenação de Equipe — Design Técnico

> Design reconstruído a partir dos componentes React/TypeScript e das consultas Supabase do módulo Coordenador. 🟢 comportamento observado; 🟡 inferência; 🔴 lacuna.

## Interface

A unidade é composta por páginas React protegidas pelo roteamento central de `src/App.tsx`; não há endpoint HTTP próprio identificado. 🟢

| Símbolo | Assinatura | Retorno | Observação |
|---------|-----------|---------|------------|
| `CoordenadorInicio` | `()` | `JSX.Element` | Carrega identidade, equipe, requests, ciclo aberto, leituras pendentes e agregações do dashboard. 🟢 |
| `CoordenadorEquipe` | `()` | `JSX.Element` | Lista membros, progresso e ações de associação, exportação e solicitação de feedback de cliente. 🟢 |
| `CoordenadorPendentes` | `()` | `JSX.Element` | Consulta requests dentro da janela de pendências, agrupa por avaliador e permite filtros e cancelamento. 🟢 |
| `CoordenadorHistorico` | `()` | `JSX.Element` | Consulta histórico de feedbacks e reutiliza padrões da visão de histórico do gestor. 🟡 |
| `ClientFeedbackDashboard` | `(teamIds: string[])` | `JSX.Element` | Exibe avaliações de clientes vinculadas ao escopo da equipe. 🟢 |
| `ClientFeedbackModal` | `(open, onOpenChange, data, isLoading)` | `JSX.Element` | Apresenta dados, notas, tags, mensagem e respostas detalhadas de uma avaliação. 🟢 |

### Dados principais

- `profiles`: identidade, nome, status ativo e relação `manager_id`. 🟢
- `coordinator_members`: associação explícita `coordinator_id` → `member_id`. 🟢
- `feedback_requests`: avaliador, avaliado, ciclo, status, prazo, envio e leitura. 🟢
- `feedback_answers` e `feedback_form_questions`: respostas e classificação das perguntas de rating. 🟢
- `feedback_cycles`: ciclo corrente e suas datas/status. 🟢
- `client_feedbacks`: avaliações externas e seus indicadores. 🟢
- `audit_logs` e `notifications`: efeitos auxiliares de ações operacionais. 🟢

## Fluxo Principal

1. `CoordenadorInicio` obtém o usuário autenticado com `supabase.auth.getUser()` e consulta seu perfil. 🟢
2. Em paralelo, consulta subordinados ativos por `profiles.manager_id` e membros explícitos por `coordinator_members`. 🟢
3. Une as duas listas e remove entradas com o mesmo `id`; o conjunto resultante forma `teamIds` junto com o próprio coordenador. 🟢
4. Consulta `feedback_requests` para os membros do escopo, relacionando ciclo, giver e receiver, e ordena por `due_date`. 🟢
5. Consulta o ciclo `open`, requests submetidos ainda não lidos e, quando aplicável, respostas de rating do ciclo. 🟢
6. Agrega em memória pendências, enviados, taxa de conclusão, atrasos, próximos vencimentos, membros sem progresso e médias de rating. 🟢
7. Renderiza cards de métricas, gráficos, alertas de ciclo/leitura, progresso, histórico comparativo e avaliações de clientes. 🟢
8. `CoordenadorEquipe` oferece a visão tabular por membro, exportação XLSX e mutações de associação ou solicitação de feedback externo. 🟢
9. `CoordenadorPendentes` restringe a lista à janela de até três dias anteriores, agrupa por giver e executa cancelamento com justificativa quando confirmado. 🟢
10. `CoordenadorHistorico` consulta o histórico e abre modais para respostas internas ou avaliações de cliente. 🟡

## Fluxos Alternativos

- **Sem usuário autenticado:** `userId` fica nulo, as queries dependentes não são habilitadas e a rota deve ser controlada pelo `ProtectedRoute`. 🟢
- **Sem equipe:** consultas que dependem de `teamIds` retornam listas vazias e os cards exibem estado vazio. 🟢
- **Sem ciclo aberto:** métricas específicas de ciclo, radar e atrasos não são calculadas; o dashboard indica que não há ciclo aberto. 🟢
- **Sem respostas de rating:** radar não é exibido como resultado; a tela informa que ainda não há avaliações enviadas. 🟢
- **Requests cancelados ou abdicados:** são excluídos das métricas de progresso. 🟢
- **Request fora da janela de atraso:** não aparece na seção de pendências atrasadas, mesmo que esteja vencido. 🟢
- **Erro de consulta:** o componente apresenta estado de erro ou vazio conforme o componente de UI; o contrato de telemetria não foi encontrado. 🟡
- **Falha ao registrar auditoria/notificação:** a operação principal pode permanecer concluída e a falha auxiliar é comunicada. 🟡
- **Avaliação de cliente negativa:** nota baixa ou `has_negative` recebe sinalização visual e pode ser aberta em detalhe. 🟢

## Dependências

- `@tanstack/react-query`: cache, habilitação condicional e carregamento das queries. 🟢
- `@/integrations/supabase/client`: autenticação e acesso direto às tabelas Supabase. 🟢
- `react-router-dom`: navegação para equipe, pendências e histórico. 🟢
- `src/components/ProtectedRoute.tsx`: proteção de rotas por sessão e papel ativo. 🟢
- `src/components/ClientFeedbackDashboard.tsx` e componentes de modal: visualização de avaliações externas. 🟢
- `src/components/CycleComparison.tsx`, `CycleClosedBanner.tsx`, `CycleDeadlineBanner.tsx`: widgets de ciclo. 🟢
- `src/components/ReminderButton.tsx`, `src/lib/createAuditLog.ts` e `src/hooks/useCreateNotification.ts`: ações auxiliares e governança. 🟢
- `recharts`: gráficos de distribuição, progresso e evolução. 🟢
- `xlsx`/exportador equivalente: geração da planilha da equipe. 🟢

## Decisões de Design Identificadas

| Decisão | Evidência no código | Confiança |
|---------|---------------------|-----------|
| Consultar o Supabase diretamente no cliente por meio de React Query. | `src/pages/coordenador/CoordenadorInicio.tsx` e demais páginas do módulo | 🟢 |
| Compor o escopo por duas relações (`manager_id` e `coordinator_members`). | `src/pages/coordenador/CoordenadorInicio.tsx` | 🟢 |
| Fazer deduplicação em memória pelo identificador do perfil. | `src/pages/coordenador/CoordenadorInicio.tsx` | 🟢 |
| Agregar métricas no cliente a partir de requests brutos. | `src/pages/coordenador/CoordenadorInicio.tsx`, `CoordenadorEquipe.tsx` | 🟢 |
| Reutilizar conceitos e componentes da visão de gestor para histórico e supervisão. | `src/pages/coordenador/CoordenadorHistorico.tsx` | 🟡 |
| Tratar auditoria e notificação como efeitos auxiliares da mutação principal. | `src/pages/coordenador/CoordenadorEquipe.tsx` | 🟡 |

## Estado Interno

- `userId`, `profile`, `team`, `requests` e `activeCycle` são dados remotos armazenados/cacheados pelo React Query. 🟢
- `teamIds` é derivado da identidade do coordenador e da equipe carregada. 🟢
- Filtros de membro, busca, status, paginação e seleção de modal são estado local dos componentes. 🟢
- Métricas como `pending`, `submitted`, `completionRate`, `overdue` e `upcoming` são derivadas em memória e não persistidas. 🟢
- Ações de cancelamento, abdicação e retomada evoluem o status de `feedback_requests` e invalidam ou atualizam as queries correspondentes. 🟢
- O conjunto `radarData` é derivado de answers de rating submetidas no ciclo aberto; seleciona os três melhores e até três membros com média abaixo de 3.0. 🟢
- O estado de loading combina as queries necessárias para evitar renderização prematura do dashboard. 🟢

## Observabilidade

- Estados visuais de carregamento, vazio e erro são apresentados por componentes da interface. 🟢
- A remoção de membro e o cancelamento de request tentam registrar `audit_logs`. 🟢
- Ações relevantes tentam criar notificações para os usuários afetados. 🟢
- Não foram identificados logs estruturados, métricas ou traces distribuídos específicos do módulo. 🔴

## Riscos e Lacunas

- 🔴 As políticas RLS e a autorização server-side das queries e mutações não foram verificadas.
- 🔴 O contrato da exportação XLSX e sua compatibilidade com todos os navegadores não foi documentado no código analisado.
- 🟡 A fronteira exata entre a visão de Coordenador e a visão de Gestor no histórico depende de componentes compartilhados.
- 🟡 O tratamento de falhas de auditoria e notificação pode variar entre os componentes e não possui contrato uniforme explícito.
- 🟡 Há queries amplas e agregações no cliente, com possível impacto de performance em equipes grandes.
