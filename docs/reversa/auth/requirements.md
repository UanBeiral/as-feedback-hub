# Unidade: Autenticação e Contexto de Papel

## Visão Geral

Mantém sessão Supabase, carrega o perfil e define o papel ativo usado pelas rotas e dashboards. 🟢

## Responsabilidades

- Observar sessão e carregar `profiles`. 🟢
- Identificar papéis e contexto gestor/coordenador. 🟢
- Proteger rotas por papel e status. 🟢
- Permitir seleção de papel ativo para usuários multi papel. 🟢

## Regras de Negócio

- Usuário inativo não acessa rotas protegidas. 🟢
- `activeRole` pode ser escolhido quando há múltiplos contextos. 🟢
- Papel permitido pode ser o papel persistido ou o papel ativo selecionado. 🟢
- Regras RLS complementares não foram verificadas. 🔴

## Requisitos Funcionais

| ID | Requisito | Prioridade | Critério de Aceite |
|----|-----------|-----------|-------------------|
| RF-01 | Detectar sessão atual e mudanças de autenticação. | Must | Login/logout atualiza o contexto sem sessão obsoleta. |
| RF-02 | Carregar perfil por `userId`. | Must | Perfil e flags ficam disponíveis às telas. |
| RF-03 | Selecionar papel ativo. | Must | Usuário multi papel escolhe contexto e navegação respeita escolha. |
| RF-04 | Proteger rotas por papel/status. | Must | Papel não permitido ou usuário inativo é bloqueado. |

## Requisitos Não Funcionais

| Tipo | Requisito inferido | Evidência | Confiança |
|------|--------------------|-----------|-----------|
| Segurança | Toda rota interna deve exigir sessão e papel. | `ProtectedRoute.tsx` | 🟢 |
| Consistência | Perfil deve ser atualizado após mudança de sessão. | `AuthContext.tsx` | 🟢 |
| Disponibilidade | Estado de carregamento deve evitar renderização antes do perfil. | `AuthContext.tsx` | 🟡 |

## Critérios de Aceitação

```gherkin
Dado um usuário autenticado ativo
Quando abrir uma rota permitida
Então o conteúdo será renderizado

Dado usuário inativo ou papel não permitido
Quando abrir rota protegida
Então o acesso será bloqueado

Dado usuário com múltiplos papéis
Quando escolher papel ativo
Então o contexto e a navegação refletirão a escolha
```

## Prioridade (MoSCoW)

| Requisito | MoSCoW | Justificativa |
|-----------|--------|---------------|
| Sessão, perfil e proteção | Must | Base de segurança da aplicação. |
| Seleção de papel | Must | Necessária para multi contexto. |
| Persistência de preferência | Should | Melhora continuidade, contrato não confirmado. |

## Rastreabilidade de Código

| Arquivo | Função / Classe | Cobertura |
|---------|-----------------|-----------|
| `src/contexts/AuthContext.tsx` | sessão, perfil e `setActiveRole` | 🟢 |
| `src/components/ProtectedRoute.tsx` | bloqueio por papel/status | 🟢 |
| `src/App.tsx` | composição das rotas | 🟢 |
