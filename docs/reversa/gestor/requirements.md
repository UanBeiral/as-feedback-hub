# Unidade: Gestor

## Visão Geral

A unidade do gestor oferece acompanhamento operacional da equipe dentro dos ciclos de feedback. Ela consolida progresso, pendências, histórico, solicitações de avaliações de clientes e relatórios conforme o papel ativo e as configurações da empresa.

## Responsabilidades

- Listar subordinados diretos e acompanhar seu progresso.
- Exibir requests pendentes, atrasados, enviados e não lidos.
- Permitir ações operacionais sobre pendências e histórico.
- Disponibilizar relatórios e agenda quando habilitados.

## Regras de Negócio

- O gestor visualiza membros associados por `manager_id` e seus requests relacionados. 🟢
- Progresso exclui requests cancelados e abdicados; enviados contam como concluídos. 🟢
- Pendências principais são requests `pending` ou `draft`, considerando vencimento e tolerância visual. 🟢
- Acesso do gestor a relatórios e agenda pode ser controlado por `company_settings`. 🟢
- A remoção de membro e ações sensíveis devem registrar auditoria e tentar notificar envolvidos. 🟢
- A política efetiva de escopo dos dados depende também de RLS no Supabase. 🟡
- A regra de autorização server-side para relatórios do gestor não foi confirmada. 🔴

## Validação humana — 2026-08-25

- 🟢 Gestores ficam limitados à própria equipe autorizada e devem respeitar `view_history_of` quando a permissão estiver configurada.
- 🟢 Flags ausentes/indefinidas significam acesso negado; parâmetros de URL não ampliam o escopo.
- 🔴 A matriz de policies efetiva no banco de produção ainda não foi extraída integralmente.

## Requisitos Funcionais

| ID | Requisito | Prioridade | Critério de Aceite |
|----|-----------|-----------|-------------------|
| RF-01 | Exibir dashboard do gestor com métricas do ciclo aberto e da equipe. | Must | Dado um gestor com equipe e ciclo aberto, quando abrir o início, então vê totais, progresso, pendências e atrasos calculados. |
| RF-02 | Listar membros diretos com status, progresso e feedbacks pendentes. | Must | Dado um membro ativo, quando a equipe carregar, então seus requests são agregados sem incluir cancelados ou abdicados no progresso. |
| RF-03 | Exibir pendências agrupadas por avaliador com busca e filtro de status. | Must | Dado requests `pending` ou `draft`, quando aplicar filtro ou busca, então somente os itens correspondentes aparecem. |
| RF-04 | Cancelar uma pendência com justificativa. | Should | Dado um request pendente, quando o gestor confirmar o cancelamento, então o status passa a `cancelled` e a justificativa é auditada quando suportada. |
| RF-05 | Consultar histórico de feedbacks da equipe e detalhes de respostas. | Should | Dado feedback submetido, quando abrir o histórico, então os dados do ciclo, avaliador, avaliado e respostas aparecem conforme a permissão. |
| RF-06 | Solicitar avaliações de clientes para membros autorizados. | Should | Dado um membro ativo e configuração válida, quando enviar uma solicitação, então o registro de avaliação externa é criado e o estado é exibido. |
| RF-07 | Acessar relatórios operacionais e executivos quando a configuração permitir. | Should | Dado `gestor_can_access_reports = true`, quando abrir o menu, então as rotas de relatório ficam disponíveis; caso contrário, não são exibidas. |
| RF-08 | Enviar lembrete para avaliadores com pendências. | Could | Dado um avaliador com requests atrasados, quando o gestor solicitar lembrete, então a notificação correspondente é enviada ou o erro é informado. |

## Requisitos Não Funcionais

| Tipo | Requisito inferido | Evidência no código | Confiança |
|------|--------------------|---------------------|-----------|
| Segurança | Rotas exigem sessão e papel gestor, admin ou rh. | `src/App.tsx`, `src/components/ProtectedRoute.tsx` | 🟢 |
| Performance | Dashboard usa consultas e agregações independentes com React Query. | `src/pages/gestor/GestorInicio.tsx` | 🟢 |
| Disponibilidade | Falha de auditoria/notificação não deve bloquear toda ação operacional. | `src/pages/gestor/GestorEquipe.tsx` | 🟡 |

## Critérios de Aceitação

```gherkin
Dado um gestor autenticado com subordinados ativos
Quando ele abrir o dashboard
Então o sistema mostra o ciclo aberto e o progresso da equipe

Dado um request pending ou draft com prazo vencido
Quando o gestor abrir pendências
Então o item aparece com indicação de atraso e pode ser filtrado

Dado um request pendente selecionado
Quando o gestor cancelar com justificativa
Então o request fica cancelled e não entra no progresso concluído ou pendente

Dado um gestor sem acesso global a relatórios
Quando ele abrir a navegação
Então o item de relatórios não fica disponível

Dado uma falha ao registrar auditoria ou notificar
Quando a ação principal já tiver sido persistida
Então o sistema informa a falha auxiliar sem desfazer a operação principal
```

## Prioridade (MoSCoW)

| Requisito | MoSCoW | Justificativa |
|-----------|--------|---------------|
| Dashboard e progresso da equipe | Must | Fluxo central de supervisão. |
| Pendências e status | Must | Ação operacional recorrente. |
| Histórico | Should | Necessário para acompanhamento, mas não bloqueia o ciclo. |
| Relatórios | Should | Capacidade relevante, condicionada a configuração. |
| Solicitação de cliente | Should | Complementa o feedback interno. |
| Lembretes | Could | Ação auxiliar com alternativas de notificação. |

## Rastreabilidade de Código

| Arquivo | Função / Classe | Cobertura |
|---------|-----------------|-----------|
| `src/pages/gestor/GestorInicio.tsx` | dashboard e agregação de equipe | 🟢 |
| `src/pages/gestor/GestorEquipe.tsx` | gestão de membros e progresso | 🟢 |
| `src/pages/gestor/GestorPendentes.tsx` | pendências e cancelamento | 🟢 |
| `src/pages/gestor/GestorHistorico.tsx` | histórico e ações sobre feedbacks | 🟢 |
| `src/components/layout/AppSidebar.tsx` | visibilidade de relatórios e agenda | 🟢 |
| `src/components/ReminderButton.tsx` | lembretes de pendências | 🟢 |
