# Unidade: Notificações e Configurações — Design Técnico

## Interface

| Símbolo | Assinatura | Retorno | Observação |
|---------|-----------|---------|------------|
| `useCompanySettings` | `()` | `settings/query state` | Lê valores de `company_settings`. 🟢 |
| `createNotification` | `(userId, type, title, message?, link?)` | `Promise<void>` | Insere notificação interna. 🟢 |
| `AdminConfiguracoes` | `()` | `JSX.Element` | Formulário administrativo de settings. 🟢 |

## Fluxo Principal

1. Administração consulta settings por chave. 🟢
2. Formulário altera valores e persiste. 🟢
3. Consumidores consultam flags/branding. 🟢
4. Operações chamam `createNotification` para inserir evento dirigido. 🟢

## Fluxos Alternativos

- Chave ausente: usar default da tela, se existente. 🟡
- Erro de save: manter valor anterior. 🟢
- Falha de notificação: informar efeito auxiliar. 🟡

## Dependências

Supabase, React Query, `company_settings`, `notifications` e componentes administrativos. 🟢

## Decisões de Design Identificadas

| Decisão | Evidência | Confiança |
|---------|-----------|-----------|
| Settings genéricos por chave/valor. | `AdminConfiguracoes.tsx` | 🟢 |
| Hook de notificação reutilizável. | `useCreateNotification.ts` | 🟢 |

## Estado Interno

Valores remotos são cacheados; formulário mantém alterações até salvar. 🟢

## Observabilidade

Falhas são comunicadas por UI; auditoria/telemetria de notificação não foi encontrada. 🟡

## Riscos e Lacunas

- 🔴 Confirmar unicidade das chaves, delivery e leitura.
- 🟡 Confirmar defaults e tipos de cada setting.
