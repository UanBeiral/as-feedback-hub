# Unidade: Administração, Design Técnico

## Interface

A unidade é composta por rotas React protegidas e páginas administrativas. Não expõe endpoint HTTP próprio; acessa o Supabase pelo cliente JavaScript.

| Símbolo | Assinatura | Retorno | Observação |
|---------|-----------|---------|------------|
| `AdminDashboard` | `()` | `JSX.Element` | Consolida métricas, alertas e atividade administrativa. |
| `AdminUsuarios` | `()` | `JSX.Element` | Lista e muta perfis, departamentos e flags. |
| `AdminPermissoes` | `()` | `JSX.Element` | Mantém permissões e relações de avaliação. |
| `ensureReversePeerPermission` | `(reviewerId: string, revieweeId: string, cycleId: string \| null)` | `Promise<void>` | Garante a relação reversa e request do ciclo ativo quando aplicável. |
| `AdminCiclos` | `()` | `JSX.Element` | Cria e administra o ciclo de vida dos ciclos. |
| `AdminRelatorios` | `()` | `JSX.Element` | Consulta relatórios operacionais e exporta CSV. |
| `AdminRelatorioFeedback` | `()` | `JSX.Element` | Gera PDF individual ou consolidado e envia por email. |

## Fluxo Principal

1. `ProtectedRoute` valida sessão, perfil e papel (`admin` ou `rh`) antes de renderizar o `AppLayout` administrativo em `src/App.tsx`.
2. `AppLayout` e `AppSidebar` derivam o menu a partir do papel ativo e das configurações globais.
3. Cada página carrega dados com `useQuery` e consulta tabelas Supabase relacionadas ao fluxo.
4. Mutations persistem alterações e invalidam ou recarregam os dados exibidos.
5. Operações relevantes registram auditoria e podem criar notificações.
6. O dashboard agrega dados em memória para cards, gráficos e alertas.

## Fluxos Alternativos

- **Usuário com múltiplos contextos:** `AuthContext` permite selecionar papel ativo; admin/RH pode também assumir visão de gestor quando habilitado.
- **Abertura de ciclo com concorrência:** `AdminCiclos` alerta quando já há ciclo aberto da mesma frequência antes de prosseguir.
- **Permissão peer-to-peer:** a criação chama a lógica de relação reversa para manter A→B e B→A.
- **Falha de persistência:** a tela exibe erro/toast e não deve confirmar a alteração como concluída.
- **Falha de auditoria ou notificação:** o fluxo principal pode continuar, conforme o padrão observado em operações de equipe.
- **Relatório sem dados:** relatórios mostram estado vazio e não geram arquivo de dados inexistente.

## Dependências

- `src/components/ProtectedRoute.tsx`: autenticação e autorização de rota.
- `src/contexts/AuthContext.tsx`: sessão, perfil e papel ativo.
- `src/components/layout/AppLayout.tsx` e `AppSidebar.tsx`: layout e navegação contextual.
- `src/integrations/supabase/client.ts`: cliente de autenticação, banco e funções.
- `@tanstack/react-query`: cache, carregamento e sincronização de consultas.
- `src/lib/generateFeedbackRequests.ts`: geração de requests na abertura de ciclo.
- `src/lib/createAuditLog.ts`: registro de operações administrativas.
- `html2canvas` e `jspdf`: renderização e montagem do PDF executivo.

## Decisões de Design Identificadas

| Decisão | Evidência no código | Confiança |
|---------|---------------------|-----------|
| Roteamento administrativo protegido por papel | `src/App.tsx`, `src/components/ProtectedRoute.tsx` | 🟢 |
| Supabase é acessado diretamente pelas páginas | `src/pages/admin/*.tsx`, `src/integrations/supabase/client.ts` | 🟢 |
| Estado remoto usa React Query | `src/pages/AdminDashboard.tsx`, `src/pages/admin/AdminRelatorios.tsx` | 🟢 |
| Permissões peer-to-peer são bidirecionais | `src/pages/admin/AdminPermissoes.tsx` | 🟢 |
| Relatório executivo é montado como HTML antes do PDF | `src/pages/admin/AdminRelatorioFeedback.tsx` | 🟢 |
| RLS complementa a segurança de UI | ausência de confirmação nas páginas e uso amplo de queries | 🟡 |

## Estado Interno

- Estado remoto: perfis, ciclos, requests, respostas, formulários, departamentos, auditoria e configurações ficam no Supabase e são lidos por queries.
- Estado de tela: filtros, tabs, paginação, seleção de colunas, modais e status de geração usam `useState` local.
- Estado de contexto: sessão, perfil, papel ativo e necessidade de seleção ficam no `AuthContext`.
- Estado de ciclo: o status persistido varia entre `draft`, `open`, `closed`, `published` e `archived`.

## Observabilidade

- Toasts informam sucesso e falha de operações, exportações e geração de relatórios.
- `console.error` e `console.warn` registram falhas de persistência, análise de IA, email e cache.
- `audit_logs` preserva operações administrativas e alterações sensíveis.
- Não foi confirmada instrumentação central de métricas ou traces. 🔴

## Riscos e Lacunas

- 🔴 O contrato e a autorização das Edge Functions administrativas não foram confirmados.
- 🔴 As políticas RLS e a cobertura de testes de integração não foram validadas.
- 🟡 A invalidação de cache após todas as mutations varia entre páginas e precisa ser conferida por fluxo.
- 🟡 Há rotas duplicadas de coordenador no roteador, embora o componente administrativo continue funcional.
