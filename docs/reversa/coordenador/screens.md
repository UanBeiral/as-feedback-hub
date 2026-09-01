# Telas — unit `coordenador`

> Gerado pelo Visor (Reversa) em 2026-08-28 a partir de screenshots do sistema em produção (`aesfeedbackinterno.vercel.app`).
> Escala de confiança: 🟢 CONFIRMADO (visível no screenshot) · 🟡 INFERIDO · 🔴 LACUNA
>
> **Menu lateral do coordenador (ordem observada):** Anotações (▸ Minhas Anotações), Relatórios (▸ Dados e Filtros, Emitir Relatório), Início, Minha Equipe, Feedbacks Pendentes, Histórico da Equipe, Meus Feedbacks, Meu Histórico, Meu Perfil, Compromissos, Sair 🟢
> Badge de papel no cabeçalho: **"Coordenador"** em roxo/violeta (Admin usa cinza) 🟢

---

## Início (Dashboard do Coordenador)

- **Rota:** `/coordenador` · **Arquivo:** `src/pages/coordenador/CoordenadorInicio.tsx`
- **Screenshot:** `screenshots/inicio.png`
- **Estado capturado:** equipe sem pendências, sem anotações

### Estrutura

1. Saudação personalizada: "Olá, Uanderson!" + data por extenso ("Sexta-Feira, 28 De Agosto De 2026") 🟢
2. **Banner "Dar Feedback para alguém"** (mesmo CTA do admin) 🟢
3. **Painel "Minhas Anotações"** embutido, com ação **+ Anotar** e estado vazio: "Nenhuma anotação ainda. Comece a anotar!" 🟢
4. **4 cards KPI:** Membros da Equipe (1, "Clique para ver a equipe"), Pendências (0, "Equipe em dia!"), Taxa de Conclusão (0%, "Precisa de atenção"), Ciclo Atual ("360 Feedback - Setembro/2026", "Até 30/09/2026") 🟢

---

## Minha Equipe

- **Rota:** `/coordenador/equipe` · **Arquivo:** `src/pages/coordenador/CoordenadorEquipe.tsx`
- **Screenshot:** `screenshots/minha-equipe.png`
- **Estado capturado:** 1 membro, sem progresso

- Mesma estrutura da tela homônima do admin: Exportar Excel, + Adicionar Membro, tabela (Nome, Cargo, Status, Pendentes de Enviar, Enviados, Pendentes de Leitura, Progresso, Ações), barra de progresso geral e total de membros 🟢
- **Diferença vs. admin:** coluna Ações tem 3 ícones — balão de feedback 💬, sino de lembrete 🔔 e ✕ remover 🟢 (admin mostra apenas ✕) — coordenador pode dar feedback/cobrar diretamente da linha 🟡

---

## Feedbacks Pendentes

- **Rota:** `/coordenador/pendentes` · **Arquivo:** `src/pages/coordenador/CoordenadorPendentes.tsx`
- **Screenshot:** `screenshots/feedbacks-pendentes.png`
- **Estado capturado:** vazio
- **Propósito:** "Feedbacks que sua equipe ainda precisa enviar no ciclo atual." 🟢

- Filtros: busca por nome, dropdown "Todos" 🟢
- Estado vazio: "Nenhum feedback pendente." 🟢
- 🔴 LACUNA: estado preenchido (lista de pendências com ação de lembrete) não capturado.

---

## Histórico da Equipe

- **Rota:** `/coordenador/historico` · **Arquivo:** `src/pages/coordenador/CoordenadorHistorico.tsx`
- **Screenshot:** `screenshots/historico-equipe.png`
- **Estado capturado:** Feedback Livre com 1 resultado
- **Propósito:** "Visualize todos os feedbacks enviados e recebidos pela sua equipe em ciclos anteriores e no ciclo atual." 🟢

- **Painel de filtros mais rico que o do admin:** Tipo de Feedback ⓘ, Status ⓘ, toggle Cancelados/Ocultos ⓘ, Data início ⓘ, Data fim ⓘ, Buscar por nome ⓘ ("Nome do avaliador ou avaliado..."), ordenação A-Z / Data 🟢
- Seção "Feedback Livre da Equipe" com card idêntico ao do admin (Para/De, Pontos Positivos, Pontos de Melhoria, Mensagem, badge de ciência, Ver Detalhes) 🟢
- Demais seções (Avaliações de Clientes, 360°) abaixo da dobra 🟡
