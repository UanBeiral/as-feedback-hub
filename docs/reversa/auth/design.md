# Unidade: Autenticação — Design Técnico

## Interface

| Símbolo | Assinatura | Retorno | Observação |
|---------|-----------|---------|------------|
| `fetchProfile` | `(userId: string)` | `Profile | null` | Consulta perfil e contexto organizacional. 🟢 |
| `setActiveRole` | `(role: string)` | `void` | Altera contexto de papel no provider. 🟢 |
| `ProtectedRoute` | `(children, allowedRoles?)` | `ReactNode` | Permite rota quando papel persistido ou ativo é aceito. 🟢 |

## Fluxo Principal

1. Provider obtém sessão inicial e observa `onAuthStateChange`. 🟢
2. Com `userId`, consulta `profiles`. 🟢
3. Deriva papéis/contextos e escolhe papel ativo. 🟢
4. `ProtectedRoute` aguarda loading, valida status e papel e renderiza ou bloqueia. 🟢

## Fluxos Alternativos

- Sem sessão: estado desautenticado. 🟢
- Perfil inexistente: acesso não autorizado/estado de erro. 🟡
- Inativo: bloqueio explícito. 🟢
- Multi papel: seletor de contexto. 🟢

## Dependências

Supabase Auth, `profiles`, `company_settings`, React Context e React Router. 🟢

## Decisões de Design Identificadas

| Decisão | Evidência | Confiança |
|---------|-----------|-----------|
| Sessão é fonte de identidade. | `AuthContext.tsx` | 🟢 |
| Autorização de UI é centralizada em `ProtectedRoute`. | `ProtectedRoute.tsx` | 🟢 |
| Contexto ativo é separado do papel persistido. | `AuthContext.tsx` | 🟢 |

## Estado Interno

Sessão, usuário, perfil, loading, erro e `activeRole` vivem no provider. 🟢

## Observabilidade

Mensagens de bloqueio e loading são visuais; logs de autenticação não foram encontrados. 🔴

## Riscos e Lacunas

- 🔴 Validar sincronização com RLS e expiração de sessão.
- 🟡 Confirmar persistência do papel ativo entre reloads.
