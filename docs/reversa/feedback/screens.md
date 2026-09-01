# Telas — unit `feedback`

> Gerado pelo Visor (Reversa) em 2026-08-28 a partir de screenshots do sistema em produção (`aesfeedbackinterno.vercel.app`).
> Escala de confiança: 🟢 CONFIRMADO (visível no screenshot) · 🟡 INFERIDO · 🔴 LACUNA
>
> As telas desta unit são rotas compartilhadas entre papéis (capturadas nos menus de Admin e Coordenador) mais a gestão de formulários, cujo domínio pertence ao feedback 360°.

---

## Minhas Anotações

- **Rota:** `/minhas-anotacoes` · **Arquivo:** `src/pages/MinhasAnotacoes.tsx`
- **Screenshot:** `screenshots/minhas-anotacoes.png`
- **Estado capturado:** vazio
- **Contexto:** item "Anotações ▸ Minhas Anotações" no menu de papéis avaliadores 🟢
- **Nota de mapeamento:** tela compartilhada; mapeada à unit `feedback` por decisão do usuário (anotações = preparação do feedback), 2026-08-28.

- Subtítulo: "Todas as suas anotações organizadas por ciclo e pessoa" 🟢
- 2 cards KPI: Total de anotações (0), Pessoas anotadas (0) 🟢
- Busca "por nome..." 🟢
- Estado vazio: ilustração + "Você ainda não fez anotações. Clique em 'Nova Anotação' para começar!" 🟢
- Ação de topo: **+ Nova Anotação** 🟢
- 🔴 LACUNA: modal/fluxo de criação de anotação não capturado (inclusive o fluxo de anotação por áudio sugerido pelo badge "Áudio" em Anotações Realizadas).

---

## Meus Feedbacks

- **Rota:** `/meus-feedbacks` · **Arquivo:** `src/pages/MeusFeedbacks.tsx`
- **Screenshot:** `screenshots/meus-feedbacks.png` (capturado com papel Coordenador)
- **Estado capturado:** vazio
- **Propósito:** "Gerencie seus feedbacks pendentes, enviados e abdicados." 🟢

- **3 cards KPI coloridos:** Precisam da sua atenção (0, amarelo), Enviados com sucesso (0, verde), **Abdicados** (0, roxo) 🟢 — confirma o estado "abdicado" na máquina de estados de `feedback_requests` 🟡
- Filtros: busca "avaliado...", dropdown "Todos", toggle "Só pendentes" 🟢
- Ordenação: A-Z, Data, botão "Mostrar cancelados" 🟢
- Seção colapsável: "Feedback Livre — Enviados por mim (0)" 🟢
- 🔴 LACUNA: card de request pendente (formulário de resposta 360°) não capturado — é a tela central do fluxo de avaliação; `src/pages/FeedbackForm.tsx` também sem captura.

---

## Meu Histórico

- **Rota:** `/historico` · **Arquivo:** `src/pages/Historico.tsx`
- **Screenshot:** `screenshots/meu-historico.png` (capturado com papel Coordenador)
- **Estado capturado:** vazio
- **Propósito:** "Visualize todos os feedbacks que você recebeu em ciclos anteriores e no ciclo atual." 🟢

- Abas: **360°** (ativa) | **Feedback Livre** 🟢
- Estado vazio: "Nenhum histórico de feedback disponível." 🟢
- 🔴 LACUNA: estado preenchido (visualização do feedback recebido, devolutiva) não capturado; `src/pages/HistoricoPessoa.tsx` sem captura.

---

## Formulários

- **Rota:** `/admin/formularios` · **Arquivo:** `src/pages/admin/AdminFormularios.tsx`
- **Screenshots:** `screenshots/formularios.png`, `formularios-modal-novo.png`
- **Estados capturados:** listagem preenchida; modal com validação nativa disparada
- **Nota de mapeamento:** rota administrativa, mas o domínio (templates de perguntas dos ciclos) pertence à unit `feedback` conforme `traceability/code-spec-matrix.md`.

### Listagem

- Propósito: "Gerencie os formulários de feedback 360° e de avaliação de clientes externos." 🟢
- **Abas:** Formulários 360° (ativa) | Formulários de Cliente Externo 🟢
- Tabela: Nome, Descrição, Status (badge Inativo/Ativo), Ações (**Perguntas** primário, **Editar**, link Ativar/Desativar) 🟢
- Registros visíveis: "Pesquisa de Clima" (Inativo), "Formulário 360 - Quinzenal" ("modelo Do More / Do Less / Continue", Ativo) 🟢
- Ação de topo: **+ Novo Formulário** 🟢

### Modal "Novo Formulário"

- Campos: Nome (obrigatório — tooltip nativo "Preencha este campo." capturado), Descrição (textarea); Cancelar/Salvar 🟢
- 🔴 LACUNA: editor de perguntas (botão "Perguntas") não capturado — estrutura das questões (tipos, escala, ordem) sem evidência visual.

---

## Caderno do Ciclo (widget de anotações)

- **Acesso:** botão flutuante amarelo (📖) presente no canto inferior direito de todas as telas autenticadas 🟢 (capturado no dashboard do colaborador)
- **Screenshots:** `screenshots/caderno-do-ciclo-painel.png` (painel lateral), `caderno-do-ciclo-widget.png` (widget compacto flutuante)
- **Estados capturados:** vazio, nas duas apresentações

### Painel lateral "Caderno do Ciclo" ⓘ

- Subtítulo: nome do ciclo ativo ("360 Feedback - Segunda Quinzena (agosto/2026)") 🟢
- Campo **"Sobre quem?"** ⓘ — dropdown de colaborador 🟢
- Textarea: "Anote observações, rascunhos ou informações relevantes para o ciclo..." 🟢
- Botões: **🎙 Gravar Áudio** e **Salvar** 🟢 — origem do badge "Áudio" visto em Anotações Realizadas (anotações podem ser ditadas/transcritas) 🟡
- Estado vazio: "Nenhuma anotação ainda. 💡 Anote ao longo do ciclo para facilitar o preenchimento dos feedbacks!" 🟢

### Widget compacto (flutuante)

- Mesma função em formato reduzido: dropdown de pessoa, campo "Observação, rascunho ou insight...", link "Áudio", atalho **Ctrl+Enter** para Salvar 🟢

---

## Modal "Dar Feedback Livre"

- **Acesso:** banner "Dar Feedback para alguém" presente no topo dos dashboards de todos os papéis 🟢 (capturado no Início do gestor)
- **Screenshots:** `screenshots/dar-feedback-livre-modal.png`, `dar-feedback-livre-modal-2.png` (rolagem)

### Campos

| Campo | Tipo | Placeholder |
|---|---|---|
| Para | select de colaborador | "Selecione um colaborador" |
| Pontos Positivos | textarea | "O que essa pessoa faz bem?" |
| Pontos de Melhoria | textarea | "O que essa pessoa poderia melhorar?" |
| Mensagem Livre | textarea | "Algo mais que queira compartilhar?" |

### Opções sensíveis

- ☐ **"Enviar anonimamente** (seu nome não será exibido para o destinatário)" 🟢
- ☐ **Denúncia de situação grave** (destaque vermelho): "Marque esta opção se o conteúdo envolver situações graves como assédio moral, assédio sexual, discriminação, abuso de poder, conflitos éticos ou condutas que violem as políticas da empresa. **Ao marcar, o destinatário não terá acesso a este feedback — ele será visível apenas para gestores e administradores responsáveis.**" 🟢 — canal de denúncia embutido no feedback livre, com regra de visibilidade restrita 🟢

- Ações: Cancelar / **Enviar Feedback** (desabilitado sem preenchimento) 🟢

---

## Variantes por papel (capturas adicionais)

- `screenshots/meus-feedbacks-colaborador.png` e `meus-feedbacks-gestor.png` — a tela Meus Feedbacks é idêntica entre papéis (muda apenas o menu lateral) 🟢
- `screenshots/meu-historico-colaborador.png` e `meu-historico-gestor.png` — idem para Meu Histórico 🟢
