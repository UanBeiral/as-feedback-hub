# Spec Impact Matrix

| Componente | Dados afetados | Funcionalidades impactadas | Confiança |
|---|---|---|---|
| `AuthContext` / `ProtectedRoute` | `profiles`, sessão | Todas as rotas protegidas, papel ativo e isolamento de UI | 🟢 CONFIRMADO |
| `AdminCiclos` / `generateFeedbackRequests` | `feedback_cycles`, `feedback_permissions`, `feedback_requests` | Abertura, fechamento e progresso de ciclos | 🟢 CONFIRMADO |
| `FeedbackForm` | `feedback_requests`, `feedback_answers` | Rascunho, envio, validação e histórico | 🟢 CONFIRMADO |
| `AdminRelatorios` | `client_feedbacks`, `free_feedbacks`, `feedback_requests` | CSV, preview, métricas e ranking de engajamento | 🟢 CONFIRMADO |
| `AdminRelatorioFeedback` | `feedback_requests`, `feedback_answers`, caches de IA | PDF, comparação de ciclos e email | 🟢 CONFIRMADO |
| `ClientFeedbackPage` | `client_feedbacks`, formulários de cliente | Avaliação pública e alertas de negatividade | 🟢 CONFIRMADO |
| `AppSidebar` / flags | `company_settings`, `profiles` | Exibição de menus e relatórios por papel | 🟢 CONFIRMADO |
| Edge Functions de notificação/IA | `notifications`, caches, email | Notificações, análise e envio de relatórios | 🟡 INFERIDO |
| Migrations/RLS | todas as tabelas | Segurança, integridade e autorização efetiva | 🔴 LACUNA |

## Impacto transversal

Mudanças em `profiles`, `feedback_requests` ou `feedback_cycles` afetam dashboards, históricos, relatórios e notificações. Mudanças em `feedback_forms` ou perguntas afetam o formulário e a interpretação das respostas.
