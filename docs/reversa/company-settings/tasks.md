# Unidade: Configurações da Empresa — Tarefas

## Pré-requisitos

- [ ] Schema/RLS e catálogo de chaves.

## Tarefas

- [ ] T-01, Definir catálogo, tipos e defaults. Origem: `src/pages/admin/AdminConfiguracoes.tsx`. Pronto quando cada campo tiver contrato. Confiança: 🔴.
- [ ] T-02, Implementar query de settings. Origem: `src/hooks/useCompanySettings.ts`. Pronto quando loading/erro/ausência forem tratados. Confiança: 🟢.
- [ ] T-03, Implementar formulário e mutação. Origem: `AdminConfiguracoes.tsx`. Pronto quando save atualizar consumidores. Confiança: 🟢.
- [ ] T-04, Validar RLS e concorrência de edição. Origem: migrations. Pronto quando apenas admin autorizado puder alterar. Confiança: 🔴.

## Tarefas de Teste

- [ ] TT-01, leitura e save de cada tipo.
- [ ] TT-02, chave ausente e erro.
- [ ] TT-03, isolamento administrativo. 🔴

## Ordem Sugerida

1. Catálogo/schema; 2. hook; 3. formulário; 4. segurança.

## Lacunas Pendentes (🔴)

- Confirmar catálogo, defaults, tipos e RLS.
