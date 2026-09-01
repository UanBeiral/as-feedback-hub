# Matriz Código–Spec

> Matriz de cobertura estimada dos arquivos principais do legado. 🟢 cobertura direta; 🟡 cobertura compartilhada/inferida; n/a não aplicável.

| Arquivo do legado | Unit correspondente | Cobertura |
|---|---|---|
| `src/main.tsx` | `auth/`, arquitetura global | 🟡 |
| `src/App.tsx` | `auth/`, todas as units roteadas | 🟢 |
| `src/contexts/AuthContext.tsx` | `auth/` | 🟢 |
| `src/components/ProtectedRoute.tsx` | `auth/` | 🟢 |
| `src/pages/admin/AdminDashboard.tsx` | `admin/` | 🟢 |
| `src/pages/admin/AdminUsuarios.tsx` | `admin/` | 🟢 |
| `src/pages/admin/AdminPermissoes.tsx` | `admin/`, `feedback/` | 🟢 |
| `src/pages/admin/AdminCiclos.tsx` | `admin/`, `feedback/` | 🟢 |
| `src/pages/admin/AdminFormularios.tsx` | `feedback/` | 🟡 |
| `src/pages/admin/AdminConfiguracoes.tsx` | `company-settings/`, `notifications/` | 🟢 |
| `src/pages/admin/AdminRelatorios.tsx` | `reports/` | 🟢 |
| `src/pages/admin/AdminRelatorioFeedback.tsx` | `reports/` | 🟢 |
| `src/pages/gestor/*.tsx` | `gestor/` | 🟢 |
| `src/pages/coordenador/*.tsx` | `coordenador/` | 🟢 |
| `src/pages/colaborador/ColaboradorAvaliacoesCliente.tsx` | `colaborador/` | 🟢 |
| `src/pages/colaborador/ColaboradorDashboardClientes.tsx` | `colaborador/` | 🟢 |
| `src/pages/colaborador/ColaboradorHistoricoEquipe.tsx` | `colaborador/` | 🟢 |
| `src/pages/colaborador/ColaboradorRelatoriosClientes.tsx` | `colaborador/`, `reports/` | 🟢 |
| `src/pages/public/ClientFeedbackPage.tsx` | `public/` | 🟢 |
| `src/lib/generateFeedbackRequests.ts` | `feedback/` | 🟢 |
| `src/hooks/useCompanySettings.ts` | `company-settings/`, `notifications/` | 🟢 |
| `src/hooks/useCreateNotification.ts` | `notifications/` | 🟢 |
| `src/components/ClientFeedbackDashboard.tsx` | `colaborador/`, `coordenador/`, `public/` | 🟡 |
| `src/components/RequestClientFeedbackModal.tsx` | `colaborador/`, `gestor/`, `coordenador/` | 🟡 |
| `src/components/CycleComparison.tsx` | `feedback/`, `dashboard` | 🟡 |
| `src/lib/createAuditLog.ts` | `admin/`, `gestor/`, `coordenador/` | 🟢 |
| `supabase/migrations/*` | todas as units de dados | 🟡 |
| `supabase/functions/analyze-feedback/*` | `reports/` | 🟡 |
| `supabase/functions/analyze-cycle/*` | `reports/` | 🟡 |

## Resumo

- Cobertura direta: 🟢 para os fluxos e arquivos principais identificados pelo Scout/Archaeologist.
- Cobertura compartilhada: 🟡 para componentes transversais, migrations e contratos de Edge Functions.
- Lacunas: 🔴 políticas RLS detalhadas, contratos server-side e alguns componentes compartilhados não possuem especificação completa.
