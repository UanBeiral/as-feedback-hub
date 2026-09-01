# Unidade: Autenticação — Tarefas

## Pré-requisitos

- [ ] Supabase Auth, tabela `profiles` e rotas definidas.
- [ ] Catálogo de papéis e política RLS. 🔴

## Tarefas

- [ ] T-01, Implementar provider de sessão e listener. Origem: `src/contexts/AuthContext.tsx`. Pronto quando login/logout refletirem no contexto. Confiança: 🟢.
- [ ] T-02, Implementar `fetchProfile` e derivação de papéis. Origem: `AuthContext.tsx`. Pronto quando perfil e contexto forem carregados. Confiança: 🟢.
- [ ] T-03, Implementar seleção de papel ativo. Origem: `AuthContext.tsx`. Pronto quando multi papel puder alternar. Confiança: 🟢.
- [ ] T-04, Implementar `ProtectedRoute`. Origem: `src/components/ProtectedRoute.tsx`. Pronto quando sessão, status e papel forem validados. Confiança: 🟢.
- [ ] T-05, Validar expiração/RLS. Origem: Supabase Auth/migrations. Pronto quando testes de segurança passarem. Confiança: 🔴.

## Tarefas de Teste

- [ ] TT-01, login, logout e sessão expirada.
- [ ] TT-02, perfil ausente/inativo.
- [ ] TT-03, papéis simples e múltiplos.
- [ ] TT-04, RLS. 🔴

## Ordem Sugerida

1. Provider; 2. perfil/papéis; 3. route guard; 4. segurança.

## Lacunas Pendentes (🔴)

- Confirmar RLS, persistência de `activeRole` e comportamento de perfil ausente.
