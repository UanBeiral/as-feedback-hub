# Unidade: Relatórios

## Visão Geral

Consulta, filtra, agrega, visualiza e exporta relatórios de feedback 360°, clientes e engajamento, incluindo relatório executivo em PDF/email. 🟢

## Responsabilidades

- Filtrar e ordenar resultados. 🟢
- Exibir preview e tabelas com limites de linhas. 🟢
- Calcular conclusão, engajamento e comparação de ciclos. 🟢
- Exportar CSV/PDF e enviar relatório executivo quando disponível. 🟢

## Regras de Negócio

- Preview limita 50 linhas e tabela 100. 🟢
- Engajamento usa ciclos fechados e exclui pessoas sem requests. 🟢
- Relatório executivo exige ciclo e pessoa, salvo escopo geral; escopo específico exige avaliador. 🟢
- Relatório de cliente respeita `can_generate_reports`. 🟢
- Estruturas AI são inferidas e requerem validação. 🟡

## Requisitos Funcionais

| ID | Requisito | Prioridade | Critério de Aceite |
|----|-----------|-----------|-------------------|
| RF-01 | Consultar relatório de clientes com filtros. | Must | Resultado contém apenas registros compatíveis. |
| RF-02 | Consultar relatório 360° por ciclo/departamento/pessoa. | Must | Filtros e agregações refletem requests/respostas. |
| RF-03 | Calcular relatório de engajamento. | Should | Apenas ciclos fechados entram no cálculo. |
| RF-04 | Exibir preview/tabela com limites. | Must | Preview ≤50 e tabela ≤100 linhas. |
| RF-05 | Exportar CSV e relatório executivo PDF. | Should | Arquivos contêm dados filtrados e formato válido. |
| RF-06 | Gerar/enviar análise executiva quando configurada. | Could | Requisitos de escopo são validados antes de gerar. |

## Requisitos Não Funcionais

| Tipo | Requisito inferido | Evidência | Confiança |
|------|--------------------|-----------|-----------|
| Performance | Limitar renderização de tabelas e usar filtros no cliente/consulta. | `AdminRelatorios.tsx` | 🟢 |
| Segurança | Rotas e relatórios respeitam papel/flags. | `ProtectedRoute`, páginas de relatórios | 🟢 |
| Disponibilidade | Falha de PDF/email deve informar erro sem perder preview. | `AdminRelatorioFeedback.tsx` | 🟡 |

## Critérios de Aceitação

```gherkin
Dado um conjunto de feedbacks
Quando o usuário filtrar e ordenar
Então preview e exportação refletirão os mesmos registros

Dado ciclos fechados com requests
Quando gerar engajamento
Então pessoas sem requests serão excluídas do denominador

Dado escopo executivo específico sem avaliador
Quando gerar relatório
Então a operação será recusada com orientação de preenchimento
```

## Prioridade (MoSCoW)

| Requisito | MoSCoW | Justificativa |
|-----------|--------|---------------|
| Relatórios filtrados 360°/cliente | Must | Capacidade principal. |
| Preview e limites | Must | Usabilidade e proteção de volume. |
| Engajamento e CSV | Should | Operação recorrente. |
| PDF/email/AI | Could | Dependem de integrações extras. |

## Rastreabilidade de Código

| Arquivo | Função / Classe | Cobertura |
|---------|-----------------|-----------|
| `src/pages/admin/AdminRelatorios.tsx` | `ClienteReport`, `Report360`, `EngajamentoReport` | 🟢 |
| `src/pages/admin/AdminRelatorioFeedback.tsx` | `buildReport`, PDF e email | 🟢 |
| `src/pages/colaborador/ColaboradorRelatoriosClientes.tsx` | relatório de clientes/CSV | 🟢 |
| `analyze-feedback`, `analyze-cycle` | análises AI | 🟡 |

## Validação humana — 2026-08-25

- 🟢 Há 12 Edge Functions no ambiente identificado; `send-report-email` recebe `POST` com `to`, `name`, `cycleName`, `filename` e `pdfBase64` e retorna códigos distintos para validação, configuração ausente e falha do Resend.
- 🟡 O contrato de `send-report-email` foi confirmado, mas `verify_jwt` pode ter override no dashboard.
- 🔴 `analyze-feedback` e `analyze-cycle` existem em produção, porém seus contratos e fontes ainda não estão versionados no repositório.
- 🔴 Antes de deploy, o `project_id` local precisa ser reconciliado com o projeto de produção.
