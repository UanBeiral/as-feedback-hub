# Unidade: Notificações e Configurações Operacionais

## Visão Geral

Centraliza configurações de empresa, branding, templates e criação de notificações internas. 🟢

## Responsabilidades

- Ler e gravar `company_settings`. 🟢
- Aplicar configurações visuais e operacionais. 🟢
- Criar notificações com destinatário, tipo, título, mensagem e link. 🟢

## Regras de Negócio

- Configurações são identificadas por chave e persistidas como valor. 🟢
- Notificação é associada a um usuário e pode conter link. 🟢
- Falha auxiliar de notificação não deve necessariamente bloquear operação principal. 🟡
- Contratos de entrega, leitura e retry não foram confirmados. 🔴

## Validação humana — 2026-08-25

- 🟢 O estado canônico de leitura é `read_at IS NULL` para não lida; não há coluna booleana `read`.
- 🟢 Comunicações de ciclo devem usar outbox persistente por destinatário, com chave de idempotência `update_id + user_id`.
- 🔴 O catálogo completo, confirmação formal de entrega e política geral de retry ainda não foram definidos.

## Requisitos Funcionais

| ID | Requisito | Prioridade | Critério de Aceite |
|----|-----------|-----------|-------------------|
| RF-01 | Consultar configurações da empresa. | Must | Chaves persistidas carregam no formulário correto. |
| RF-02 | Atualizar branding, templates e flags. | Should | Salvar altera o valor consumido pelas telas. |
| RF-03 | Criar notificação interna. | Must | Destinatário, tipo e título são persistidos. |
| RF-04 | Exibir erro de persistência sem falso sucesso. | Must | Falha mantém valor anterior e informa usuário. |

## Requisitos Não Funcionais

| Tipo | Requisito inferido | Evidência | Confiança |
|------|--------------------|-----------|-----------|
| Consistência | Chaves de configuração devem ser únicas. | `useCompanySettings.ts` | 🟡 |
| Disponibilidade | Notificação deve ser efeito auxiliar tolerante a falha. | `useCreateNotification.ts` | 🟡 |
| Segurança | Configurações administrativas exigem rota protegida. | `AdminConfiguracoes.tsx` | 🟢 |

## Critérios de Aceitação

```gherkin
Dado uma chave existente
Quando o administrador salvar novo valor
Então a configuração será persistida e consumidores poderão consultá-la

Dado um usuário destinatário
Quando uma notificação for criada
Então ela conterá tipo, título e destinatário

Dado erro de persistência
Quando salvar configuração
Então a interface informará a falha e não exibirá sucesso
```

## Prioridade (MoSCoW)

| Requisito | MoSCoW | Justificativa |
|-----------|--------|---------------|
| Leitura/gravação de settings | Must | Base das flags operacionais. |
| Criação de notificações | Must | Usada por várias operações. |
| Branding/templates | Should | Personalização relevante. |
| Retry/entrega não confirmados | Won't | Exige validação. |

## Rastreabilidade de Código

| Arquivo | Função / Classe | Cobertura |
|---------|-----------------|-----------|
| `src/pages/admin/AdminConfiguracoes.tsx` | configuração administrativa | 🟢 |
| `src/hooks/useCompanySettings.ts` | leitura de settings | 🟢 |
| `src/hooks/useCreateNotification.ts` | inserção de notificações | 🟢 |
| `company_settings` | valores operacionais | 🟢 |
