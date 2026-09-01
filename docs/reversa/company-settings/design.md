# Unidade: Configurações da Empresa — Design Técnico

## Interface

| Símbolo | Assinatura | Retorno | Observação |
|---------|-----------|---------|------------|
| `useCompanySettings` | `()` | estado de consulta | Carrega chaves/valores. 🟢 |
| `AdminConfiguracoes` | `()` | `JSX.Element` | Formulário de configuração. 🟢 |

## Fluxo Principal

1. Consultar `company_settings`. 🟢
2. Mapear chaves para campos de branding/regra. 🟢
3. Validar e persistir alteração. 🟢
4. Invalidar cache para consumidores. 🟡

## Fluxos Alternativos

- Chave ausente: default ou estado vazio. 🟡
- Erro: toast/estado de erro e valor anterior. 🟢

## Dependências

Supabase, React Query, `AdminConfiguracoes` e hooks de settings. 🟢

## Decisões de Design Identificadas

| Decisão | Evidência | Confiança |
|---------|-----------|-----------|
| Armazenar configurações genéricas por chave. | `AdminConfiguracoes.tsx` | 🟢 |
| Consumir settings via hook. | `useCompanySettings.ts` | 🟢 |

## Estado Interno

Cache remoto de settings e estado local do formulário. 🟢

## Observabilidade

Feedback visual de save/erro; sem métrica específica. 🔴

## Riscos e Lacunas

- 🔴 Catálogo, tipos, defaults e RLS.
- 🟡 Estratégia de invalidação entre abas.
