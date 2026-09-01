# Unidade: Colaborador — Design Técnico

> Design reconstruído dos fluxos opcionais de cliente, histórico e relatórios. 🟢 confirmado; 🟡 inferido; 🔴 lacuna.

## Interface

| Símbolo | Assinatura | Retorno | Observação |
|---------|-----------|---------|------------|
| `ColaboradorAvaliacoesCliente` | `()` | `JSX.Element` | Consulta avaliações, perfis ativos, filtros e solicitações. 🟢 |
| `ColaboradorDashboardClientes` | `()` | `JSX.Element` | Protege acesso por `can_view_manager_dashboard` e delega a `ClientFeedbackDashboard`. 🟢 |
| `ColaboradorHistoricoEquipe` | `()` | `JSX.Element` | Wrapper condicionado por `can_view_team_history`; reutiliza histórico do gestor. 🟢 |
| `ColaboradorRelatoriosClientes` | `()` | `JSX.Element` | Filtra avaliações e exporta CSV separado por `;`. 🟢 |
| `RequestClientFeedbackModal` | `(targetUserId, onSuccess, ...)` | `JSX.Element` | Modal compartilhado para solicitar avaliação externa. 🟡 |

## Fluxo Principal

1. A página obtém a sessão/perfil e as flags de capacidade. 🟢
2. Consulta perfis ativos para seleção e `client_feedbacks` para a listagem. 🟢
3. Deriva status, contagens, telefone mascarado e filtros ativos no cliente. 🟢
4. Solicitações são delegadas ao modal compartilhado; após sucesso, as queries são atualizadas. 🟢
5. Dashboard, histórico e relatório verificam sua flag antes de consultar ou renderizar o recurso. 🟢
6. A exportação serializa apenas os registros filtrados em CSV com separador `;`. 🟢

## Fluxos Alternativos

- **Flag falsa:** redirecionar para `/` e não disponibilizar o recurso. 🟢
- **Sem avaliações:** exibir estado vazio e contagens zeradas. 🟢
- **Sem respostas autorizadas:** ocultar/bloquear o detalhe das respostas. 🟢
- **Falha de consulta:** exibir erro e preservar filtros sem afirmar sucesso. 🟡

## Dependências

- Supabase JS e React Query para sessão, perfil e `client_feedbacks`. 🟢
- `ClientFeedbackDashboard`, `RequestClientFeedbackModal` e `GestorHistorico`. 🟢
- Roteador e `ProtectedRoute` para navegação e autenticação. 🟢
- Utilitário de CSV e máscara de WhatsApp. 🟢

## Decisões de Design Identificadas

| Decisão | Evidência | Confiança |
|---------|-----------|-----------|
| Flags independentes controlam cada capacidade. | Páginas de `src/pages/colaborador/` | 🟢 |
| Agregações são feitas no cliente. | `ColaboradorAvaliacoesCliente.tsx` | 🟢 |
| Histórico é reutilizado da visão de gestor. | `ColaboradorHistoricoEquipe.tsx` | 🟢 |
| Exportação usa CSV delimitado por ponto e vírgula. | `ColaboradorRelatoriosClientes.tsx` | 🟢 |

## Estado Interno

Filtros, paginação, seleção do modal e loading são estado local; perfil e avaliações são cacheados por React Query. 🟢

## Observabilidade

Há estados visuais de loading/erro/vazio; não foram encontrados logs ou métricas específicos. 🔴

## Riscos e Lacunas

- 🔴 RLS e autorização server-side não foram verificadas.
- 🟡 Contrato do modal compartilhado não está completo nesta unit.
- 🟡 Volume máximo suportado pela exportação CSV não foi documentado.
