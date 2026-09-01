# Telas — unit `gestor`

> Gerado pelo Visor (Reversa) em 2026-08-28 a partir de screenshots do sistema em produção (`aesfeedbackinterno.vercel.app`), capturados com um admin visualizando como gestor (badge "Gestor (Admin)" dourado).
> Escala de confiança: 🟢 CONFIRMADO (visível no screenshot) · 🟡 INFERIDO · 🔴 LACUNA
>
> **Menu lateral do gestor (ordem observada):** Anotações, Relatórios (▸ Dados e Filtros, Emitir Relatório), Início, Minha Equipe, Feedbacks Pendentes, Histórico da Equipe, Meus Feedbacks, Meu Histórico, Meu Perfil, **Avaliações de Clientes**, **Compromissos** 🟢 — os dois últimos não existem no menu do coordenador capturado anteriormente.

---

## Início (Dashboard do Gestor)

- **Rota:** `/gestor` · **Arquivo:** `src/pages/gestor/GestorInicio.tsx`
- **Screenshots:** `screenshots/inicio.png`, `inicio-2.png` (rolagem)
- **Estado capturado:** equipe de 2 membros, sem pendências, ciclo sem avaliações

### Estrutura

1. Saudação personalizada + data por extenso 🟢
2. Banner "Dar Feedback para alguém" (abre o modal de Feedback Livre — ver `feedback/screens.md`) 🟢
3. Painel "Minhas Anotações" embutido com **+ Anotar** 🟢
4. **4 cards KPI:** Membros da Equipe (2), Pendências (0, "Equipe em dia!"), Taxa de Conclusão (0%), Ciclo Atual (nome + prazo) 🟢
5. **Comparativo com Ciclo Anterior** — banner informativo: "mostrará a evolução da sua equipe — taxa de conclusão e média de avaliações recebidas — em relação ao ciclo anterior de mesma frequência e formulário. Estará disponível após o fechamento do próximo ciclo equivalente." 🟢 (exclusivo do gestor; não visto no coordenador)
6. **MELHORES DESEMPENHOS INTERNOS (360°)** — card escuro tipo ranking; vazio: "Nenhuma avaliação enviada ainda neste ciclo." 🟢
7. **ATENÇÃO NECESSÁRIA (360°)** — card; estado ok: "✅ Nenhum membro com desempenho preocupante." 🟢

---

## Minha Equipe

- **Rota:** `/gestor/equipe` · **Arquivo:** `src/pages/gestor/GestorEquipe.tsx`
- **Screenshot:** `screenshots/minha-equipe.png`
- **Estado capturado:** 2 membros ativos, 0% de progresso

- Subtítulo: "Acompanhe o progresso dos membros da sua equipe no ciclo de feedback 360° atual. Feedbacks livres e de clientes são exibidos em outras seções." 🟢
- Estrutura idêntica à do coordenador: Exportar Excel, + Adicionar Membro, colunas (Nome, Cargo, Status, Pendentes de Enviar ⓘ, Enviados ⓘ, Pendentes de Leitura ⓘ, Progresso ⓘ, Ações), progresso geral, total 🟢
- Ações por linha: 💬 dar feedback, 🔔 lembrete, ✕ remover 🟢

---

## Feedbacks Pendentes

- **Rota:** `/gestor/pendentes` · **Arquivo:** `src/pages/gestor/GestorPendentes.tsx`
- **Screenshot:** `screenshots/feedbacks-pendentes.png`
- **Estado capturado:** vazio ("Nenhum feedback pendente.")

- Idêntica à tela homônima do coordenador: busca por nome + dropdown "Todos" 🟢

---

## Histórico da Equipe

- **Rota:** `/gestor/historico` · **Arquivo:** `src/pages/gestor/GestorHistorico.tsx`
- **Screenshots:** `screenshots/historico-equipe.png`, `historico-equipe-2.png` (rolagem)
- **Estado capturado:** Feedback Livre com 1 resultado; Avaliações de Clientes (0) e 360° (0) vazios

- Filtro global "Exibir: Todos os tipos" + 3 seções colapsáveis (Feedback Livre da Equipe, Avaliações de Clientes, 360° — Ciclos de Feedback), com os mesmos filtros e card de feedback livre (Para/De, Pontos Positivos/Melhoria, Mensagem, badge de ciência, Ver Detalhes) já documentados nas variantes admin/coordenador 🟢

### Observação de paridade entre papéis

As telas de equipe/pendências/histórico do gestor e do coordenador são visual e funcionalmente equivalentes (specs `coordenador/design.md` já apontam a reutilização). As diferenças do gestor concentram-se no dashboard (Comparativo de Ciclo, Melhores Desempenhos, Atenção Necessária) e nos itens extras de menu (Avaliações de Clientes — documentada em `colaborador/screens.md` por pertencer a `ColaboradorAvaliacoesCliente.tsx` —, e Compromissos) 🟢
