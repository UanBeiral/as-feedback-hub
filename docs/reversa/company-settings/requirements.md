# Unidade: Configurações da Empresa

## Visão Geral

Permite ao administrador configurar branding, templates, motivações e flags operacionais consumidas por outras unidades. 🟢

## Responsabilidades

- Consultar configurações por chave. 🟢
- Editar valores visuais e operacionais. 🟢
- Propagar flags para menus e capacidades. 🟢

## Regras de Negócio

- Valores são persistidos em `company_settings`. 🟢
- Configurações visuais e de regra usam chave/valor. 🟢
- Defaults e catálogo completo não foram confirmados. 🔴

## Validação humana — 2026-08-25

- 🟢 `company_settings` é key/value com `id`, `key`, `value`, `updated_by` e `updated_at`.
- 🟢 O catálogo confirmado possui oito chaves, incluindo nome, logo, motivações públicas, template WhatsApp, palavras-chave de calendário e três toggles globais.
- 🟢 Os toggles são globais por escritório e aplicados por papel; não são permissões individuais em `profiles`.
- 🟡 A concorrência deve usar upsert por chave e, idealmente, `updated_at` otimista; `updated_by` ainda precisa ser populado.

## Requisitos Funcionais

| ID | Requisito | Prioridade | Critério de Aceite |
|----|-----------|-----------|-------------------|
| RF-01 | Listar configurações existentes. | Must | Administrador vê chaves e valores atuais. |
| RF-02 | Editar branding/templates/flags. | Should | Salvar atualiza a chave e consumidores a utilizam. |
| RF-03 | Tratar erro e valor ausente. | Must | Erro não gera falso sucesso; ausência usa default documentado. |

## Requisitos Não Funcionais

| Tipo | Requisito inferido | Evidência | Confiança |
|------|--------------------|-----------|-----------|
| Segurança | Somente administração altera settings. | `AdminConfiguracoes.tsx` | 🟢 |
| Consistência | Chaves devem ser únicas. | `useCompanySettings.ts` | 🟡 |

## Critérios de Aceitação

```gherkin
Dado um administrador autenticado
Quando salvar uma chave válida
Então o valor ficará persistido e poderá ser lido pelos consumidores

Dado uma falha de persistência
Quando salvar
Então a interface informará erro e manterá o valor anterior
```

## Prioridade (MoSCoW)

| Requisito | MoSCoW | Justificativa |
|-----------|--------|---------------|
| Consulta de settings | Must | Consumidores dependem dela. |
| Flags e branding | Should | Configuração operacional. |
| Chaves não catalogadas | Could | Exigem validação. |

## Rastreabilidade de Código

| Arquivo | Função / Classe | Cobertura |
|---------|-----------------|-----------|
| `src/pages/admin/AdminConfiguracoes.tsx` | edição administrativa | 🟢 |
| `src/hooks/useCompanySettings.ts` | leitura de settings | 🟢 |
| `company_settings` | persistência | 🟢 |
