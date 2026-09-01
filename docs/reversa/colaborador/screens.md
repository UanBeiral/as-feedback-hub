# Telas — unit `colaborador`

> Gerado pelo Visor (Reversa) em 2026-08-28 a partir de screenshots do sistema em produção (`aesfeedbackinterno.vercel.app`).
> Escala de confiança: 🟢 CONFIRMADO (visível no screenshot) · 🟡 INFERIDO · 🔴 LACUNA
>
> **Menu lateral do colaborador (ordem observada, capturado com usuário "uan 2" / badge "Colaborador"):** Anotações, Relatórios, Início, Meus Feedbacks, Meu Histórico, Meu Perfil 🟢 — sem itens de gestão de equipe.

---

## Início (Dashboard do Colaborador)

- **Rota:** `/dashboard` · **Arquivo:** `src/pages/Dashboard.tsx` 🟡 (rota compartilhada renderizada para o papel colaborador; `ColaboradorDashboardClientes.tsx` cobre a visão de clientes)
- **Screenshots:** `screenshots/inicio.png` (topo), `inicio-2.png`, `inicio-3.png` (rolagens)
- **Estado capturado:** sem feedbacks, sem anotações

### Estrutura

1. Saudação personalizada + data por extenso 🟢
2. Banner "Dar Feedback para alguém" 🟢
3. Painel "Minhas Anotações" embutido com **+ Anotar** 🟢
4. **4 cards KPI:** Feedbacks Pendentes (0), Feedbacks Enviados (0), Ciclo Atual ("360 Feedback - Setembro/2026"), Total de Feedbacks (0) 🟢
5. **Próximos a Vencer** — "Nenhum feedback próximo do vencimento." 🟢 (conceito de prazo/vencimento de request 🟡)
6. **Meu Progresso no Ciclo** — barra "0 de 0 feedbacks concluídos · 0%" 🟢
7. **MEU DESEMPENHO** — card escuro: "Sua média aparecerá aqui quando seus colegas avaliarem você." 🟢
8. **MINHA JORNADA** — 2 tiles: "0 ciclos participados", "0% taxa de conclusão" 🟢

---

## Avaliações de Clientes

- **Rota:** `/avaliacoes-clientes` · **Arquivo:** `src/pages/colaborador/ColaboradorAvaliacoesCliente.tsx`
- **Screenshots:** `screenshots/avaliacoes-clientes.png`, `solicitar-avaliacao-modal.png`, `solicitar-avaliacao-modal-2.png`
- **Estado capturado:** 1 pendente / 49 respondidas; modal de solicitação com aviso de duplicidade (capturado no menu do gestor — rota compartilhada entre papéis que solicitam avaliação 🟡)
- **Propósito:** "Solicite avaliações de clientes externos para qualquer colaborador." 🟢

### Página

- **2 cards KPI:** Pendentes (1, amarelo, ⓘ) e Respondidas (49, verde, ⓘ) 🟢
- **Solicitar nova avaliação:** busca de colaborador → linha com avatar/nome/cargo + botão **Solicitar** 🟢
- **Filtrar avaliações:** Colaborador ⓘ, Cliente ⓘ, WhatsApp ⓘ, Data início/fim, abas de status (Pendentes / Respondidas / Expiradas 🟡 — parcialmente visíveis) 🟢

### Modal "Solicitar Avaliação de Cliente"

- Cabeçalho: "Gere um link para o cliente avaliar **<colaborador>**. O link expira em **7 dias**." 🟢
- **Aviso de duplicidade** (amarelo): "Já existe uma solicitação pendente — Cliente <nome> (<whatsapp>) — criada em <data>. Reutilizar link existente:" com botões **Copiar link** e **Copiar WhatsApp** — "ou crie uma nova solicitação abaixo" 🟢
- Campos: Nome do cliente *, WhatsApp do cliente * (máscara), E-mail do cliente (opcional — "Se informado, o cliente receberá um e-mail com o link"), **Formulário** (dropdown; valor observado: "Atendimento Jurídico Geral") 🟢
- Ações: Cancelar / **Gerar Link** 🟢
- O link gerado leva a `/avaliacao?token=…` (fluxo documentado em `public/screens.md`) 🟢

### Telas do colaborador conhecidas do código SEM captura 🔴

- `ColaboradorDashboardClientes.tsx` (dashboard focado em clientes), `ColaboradorHistoricoEquipe.tsx`, `ColaboradorRelatoriosClientes.tsx`
