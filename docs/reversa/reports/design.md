# Unidade: Relatórios — Design Técnico

## Interface

| Símbolo | Assinatura | Retorno | Observação |
|---------|-----------|---------|------------|
| `ClienteReport` | `(profiles, onPreview)` | `JSX.Element` | Relatório de clientes. 🟢 |
| `Report360` | `(departments, cycles, profiles, onPreview)` | `JSX.Element` | Relatório 360°. 🟢 |
| `EngajamentoReport` | `(cycles, profiles)` | `JSX.Element` | Engajamento por ciclo fechado. 🟢 |
| `buildReport` | `()` | `Promise<BuiltReport|null>` | Monta relatório executivo. 🟢 |
| `renderHtmlToPdfBlob` | `(html: string)` | `Promise<Blob>` | Renderiza HTML para PDF. 🟢 |

## Fluxo Principal

1. Carregar perfis, departamentos, ciclos e dados de feedback. 🟢
2. Aplicar filtros e ordenação. 🟢
3. Agregar métricas e montar preview limitado. 🟢
4. Exportar CSV/PDF ou enviar relatório, quando solicitado. 🟢

## Fluxos Alternativos

- Sem filtro obrigatório: mostrar orientação. 🟢
- Sem dados: estado vazio. 🟢
- Falha de análise AI/email/PDF: erro específico. 🟡
- Permissão de relatório falsa: redirecionar. 🟢

## Dependências

Supabase, dados de ciclos/requests/answers, `html2canvas`, `jsPDF`, Edge Functions de análise e email. 🟢

## Decisões de Design Identificadas

| Decisão | Evidência | Confiança |
|---------|-----------|-----------|
| Preview e tabela têm limites distintos. | `AdminRelatorios.tsx` | 🟢 |
| Engajamento considera somente ciclos fechados. | `AdminRelatorios.tsx` | 🟢 |
| PDF é criado a partir de HTML. | `AdminRelatorioFeedback.tsx` | 🟢 |

## Estado Interno

Filtros, ordenação, preview, paginação e estado de geração são locais; dados são remotos/cacheados. 🟢

## Observabilidade

Feedback visual de carregamento/exportação; não foram identificados traces estruturados. 🔴

## Riscos e Lacunas

- 🔴 Contrato das funções AI/email e autorização server-side.
- 🟡 Desempenho de PDF em relatórios extensos.
