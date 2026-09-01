# Unidade: Relatórios — Tarefas

## Pré-requisitos

- [ ] Queries/tipos de feedback, ciclos, perfis e respostas.
- [ ] Bibliotecas PDF e contratos das Edge Functions. 🔴

## Tarefas

- [ ] T-01, Implementar filtros e consulta de clientes. Origem: `src/pages/admin/AdminRelatorios.tsx`. Pronto quando dados filtrados forem exibidos. Confiança: 🟢.
- [ ] T-02, Implementar relatório 360° e agregações. Origem: `AdminRelatorios.tsx`. Pronto quando ciclo/departamento/pessoa produzirem resultados corretos. Confiança: 🟢.
- [ ] T-03, Implementar engajamento por ciclos fechados. Origem: `AdminRelatorios.tsx`. Pronto quando pessoas sem requests forem excluídas. Confiança: 🟢.
- [ ] T-04, Implementar preview/tabela/paginação. Origem: `AdminRelatorios.tsx`. Pronto quando limites 50/100 forem respeitados. Confiança: 🟢.
- [ ] T-05, Implementar CSV de clientes. Origem: `ColaboradorRelatoriosClientes.tsx`. Pronto quando filtros forem preservados no arquivo. Confiança: 🟢.
- [ ] T-06, Implementar relatório executivo, PDF e email. Origem: `AdminRelatorioFeedback.tsx`. Pronto quando escopo obrigatório e falhas forem tratados. Confiança: 🟡.
- [ ] T-07, Integrar análises AI. Origem: `analyze-feedback`, `analyze-cycle`. Pronto quando contrato for validado. Confiança: 🔴.

## Tarefas de Teste

- [ ] TT-01, filtros, ordenação e limites.
- [ ] TT-02, cálculo de engajamento e comparação de ciclos.
- [ ] TT-03, CSV, PDF e erro de email.
- [ ] TT-04, permissões e RLS.

## Ordem Sugerida

1. Consulta/filtros; 2. agregações; 3. preview/exportação; 4. PDF/email/AI; 5. segurança.

## Lacunas Pendentes (🔴)

- Confirmar contratos AI/email, limites operacionais e autorização de relatórios.
