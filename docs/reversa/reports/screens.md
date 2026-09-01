# Telas — unit `reports`

> Gerado pelo Visor (Reversa) em 2026-08-28 a partir de screenshots do sistema em produção (`aesfeedbackinterno.vercel.app`).
> Escala de confiança: 🟢 CONFIRMADO (visível no screenshot) · 🟡 INFERIDO · 🔴 LACUNA

---

## Relatórios — Dados e Filtros

- **Rota:** `/admin/relatorios` · **Arquivo:** `src/pages/admin/AdminRelatorios.tsx`
- **Screenshots:** `screenshots/relatorios-dados-filtros.png`, `relatorios-dados-filtros-2.png` (rolagem da tabela)
- **Estado capturado:** aba "Clientes" preenchida (49 resultados)
- **Propósito:** "Gere relatórios personalizados com filtros, escolha de colunas e exportação em CSV." 🟢

### Abas (4 tipos de relatório)

| Aba | Conteúdo |
|---|---|
| ⭐ Clientes | Avaliações de Clientes (capturada) 🟢 |
| 💬 Livres | feedbacks livres 🟡 |
| 👥 360° | feedbacks de ciclo 🟡 |
| 📊 Engajamento | métricas de engajamento 🟡 |

### Aba "Clientes" — Avaliações de Clientes

- Ações: **Colunas** (seletor de colunas), **Preview**, **CSV** (botão primário) 🟢
- Filtros: Nota (Todas), Motivação (Todas), Profissional (Todos), De/Até (datas), Buscar cliente (nome) 🟢
- Contador de resultados ("49 resultados") 🟢
- Tabela (colunas ordenáveis): Cliente, Profissional, Nota Geral (colorida, ex. "9/10" verde), Recomendação (0–10), Motivação (badge: Avaliação / Problema / Outro), Negativo? (Sim/Não), Tipo (badge "Solicitado"), D… (coluna cortada) 🟢
- 🔴 LACUNA: abas Livres, 360° e Engajamento não capturadas; colunas à direita da tabela cortadas pelo viewport.

---

## Emitir Relatório (Relatório de Feedback)

- **Rota:** `/admin/relatorio-feedback` · **Arquivo:** `src/pages/admin/AdminRelatorioFeedback.tsx`
- **Screenshot:** `screenshots/emitir-relatorio.png`
- **Estado capturado:** formulário vazio (botões desabilitados)
- **Propósito:** "Gere relatórios executivos profissionais para impressão ou PDF." 🟢

### Formulário

| Campo | Opções observadas | Ajuda |
|---|---|---|
| Modo | "Detalhado (múltiplas páginas)" | "Capa + Resumo + Síntese + Detalhamento + Devolutiva" 🟢 |
| Escopo | "Individual Completo" | "Todos os feedbacks de uma pessoa em um ciclo" 🟢 |
| Colaborador | Selecione... | — |
| Ciclo | Selecione... | — |
| Email do relatório | email | "Pré-preenchido com o email do colaborador quando houver um selecionado." 🟢 |

- Ações: **Baixar PDF** (desabilitado sem seleção) e **Enviar por email** 🟢
- Seção informativa "Sobre os relatórios" abaixo da dobra (cortada) 🟢
- 🔴 LACUNA: demais opções dos dropdowns Modo/Escopo e o PDF resultante não capturados.
