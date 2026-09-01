# Unidade: Notificações e Configurações — Tarefas

## Pré-requisitos

- [ ] Schema e RLS de `company_settings` e `notifications`.
- [ ] Catálogo de chaves, tipos e defaults. 🔴

## Tarefas

- [ ] T-01, Implementar leitura de configurações. Origem: `src/hooks/useCompanySettings.ts`. Pronto quando chaves e loading forem tratados. Confiança: 🟢.
- [ ] T-02, Implementar formulário de configuração. Origem: `src/pages/admin/AdminConfiguracoes.tsx`. Pronto quando save e erro forem exibidos corretamente. Confiança: 🟢.
- [ ] T-03, Implementar `createNotification`. Origem: `src/hooks/useCreateNotification.ts`. Pronto quando payload completo for persistido. Confiança: 🟢.
- [ ] T-04, Definir retry, leitura e entrega. Origem: migrations e consumidores. Pronto quando contrato for aprovado. Confiança: 🔴.

## Tarefas de Teste

- [ ] TT-01, leitura/save de settings.
- [ ] TT-02, notificação com e sem campos opcionais.
- [ ] TT-03, falha auxiliar sem bloquear ação.
- [ ] TT-04, RLS administrativa. 🔴

## Ordem Sugerida

1. Schema/catalogo; 2. hooks; 3. UI; 4. entrega/segurança.

## Lacunas Pendentes (🔴)

- Confirmar tipos/defaults, unicidade e contrato de entrega.
