# Conferência contra o oráculo — 35 telas literais

> Roteiro para a validação que `parity_specs.md` exige e que nenhum teste automatizado
> substitui: comparar cada tela do sistema novo com o screenshot do legado.
>
> **Como usar**: suba o sistema (`README` § Rodando local), popule com
> `deploy/seed_demo.py` — tela vazia esconde coluna, filtro e badge, e conferir contra
> ela é marcar caixa sem provar nada —, abra a rota numa aba e o screenshot noutra, e
> marque a caixa quando conferir. O que diverge vai para
> [`conferencia-resultado.md`](conferencia-resultado.md), tela a tela; o que for
> aprovado como divergência deliberada segue depois para
> `docs/reversa/migration/screen_deviation_log.md`.
>
> O que olhar, em ordem de importância: **texto** (rótulos, mensagens, estados vazios —
> o modo literal exige diff zero), **colunas e campos** presentes, **ações** disponíveis,
> e por fim posicionamento. Cor e espaçamento vêm dos tokens e divergem por construção
> onde o design system foi aplicado.

Legenda: ✅ tela existe · ⚠️ existe parcialmente · ❌ não implementada

---

## Administração

- [x] **SCR-0003 · Painel Administrativo** ✅ `/` — **conferida**, 7 divergências
      (4 seções inteiras ausentes); ver `conferencia-resultado.md`
      `docs/reversa/admin/screenshots/dashboard.png` (+ `-2`, `-3`, `-4`)
      *Atenção*: no legado eram quatro telas de início por papel; aqui é uma rota só que
      se adapta. Confira se o conteúdo do admin bate — não o caminho.

- [x] **SCR-0007 · Usuários** ✅ `/admin/usuarios` — **conferida**, 5 divergências
      (faltam colunas, filtros, exportação e ordenação); ver `conferencia-resultado.md`
      `admin/screenshots/usuarios.png` · `usuarios-modal-novo-usuario.png`
      *Atenção*: o modal virou formulário na própria página.

- [x] **SCR-0008 · Departamentos** ✅ `/admin/departamentos` — **conferida**, 4 divergências
      `admin/screenshots/departamentos.png` · `departamentos-modal-novo.png`

- [x] **SCR-0009 · Ciclos de Feedback** ✅ `/admin/ciclos` — **conferida**, 5 divergências
      `admin/screenshots/ciclos.png` · `ciclos-modal-novo.png` (+ `-2`, `-3`) ·
      `ciclos-modal-editar.png`

- [x] **SCR-0010 · Permissões** ✅ `/admin/permissoes` — **conferida**, 6 divergências (estrutural)
      `admin/screenshots/permissoes.png` · `permissoes-modal-nova.png`
      *Atenção*: o legado tinha importação em massa; a tela nova não tem.

- [x] **SCR-0011 · Diagnóstico de Permissões** ✅ `/admin/diagnostico` — **conferida**, sem divergência
      `admin/screenshots/diagnostico.png` (+ `-2`, `-3`, `-4`)
      *Atenção*: é a tela mais densa do legado. Confira as **5 categorias**, o texto de
      cada banner explicativo e as ações em massa.

- [x] **SCR-0012 · Auditoria** ✅ `/admin/auditoria` — **conferida**, 7 divergências
      `admin/screenshots/auditoria.png` (+ `-2`, `-3`)

- [x] **SCR-0013 · Fale Conosco (admin)** ✅ `/admin/contatos` — **conferida**, 4 divergências
      `admin/screenshots/fale-conosco.png`

- [x] **SCR-0015 · Central de Atualizações** ✅ `/admin/atualizacoes` — **conferida**, sem divergência
      `admin/screenshots/atualizacoes.png`

- [x] **SCR-0024 · Configurações** ✅ `/admin/configuracoes` — **conferida**, 5 divergências
      `docs/reversa/company-settings/screenshots/configuracoes.png`
      *Atenção*: o novo tem 11 chaves contra 8 do legado (DEV-A09). As três extras são
      esperadas.

- [x] **SCR-0018 · Formulários** ✅ `/admin/formularios` — **conferida**, 4 divergências (falta a aba de cliente externo)
      `docs/reversa/feedback/screenshots/formularios.png` · `formularios-modal-novo.png`

- **SCR-0014 · Agenda** ❌ fora do corte por decisão (AMB-007, fase 2).
      `admin/screenshots/agenda.png` — não precisa conferir.

## Equipe

- [ ] **SCR-0005 · Minha Equipe (admin)** ✅ `/minha-equipe`
      `admin/screenshots/minha-equipe.png` · `minha-equipe-modal-adicionar-membro.png`

- [ ] **SCR-0006 · Histórico da Equipe (admin)** ✅ `/historico-equipe`
      `admin/screenshots/historico-equipe.png` (+ `-2`)
      *Atenção*: confira as **três seções** (livre, clientes, 360) e os filtros.

- [x] **SCR-0030 · Minha Equipe (gestor)** ✅ `/minha-equipe` — **conferida**,
      7 divergências (a tela era um painel de acompanhamento e virou listagem)
      Falta ainda conferir a variante do coordenador (SCR-0026).
      `coordenador/screenshots/minha-equipe.png` · `gestor/screenshots/minha-equipe.png`
      *Atenção*: é a mesma rota do admin, com escopo diferente. Entre com um gestor para
      conferir — o conteúdo muda, o layout não.

- [x] **SCR-0032 · Histórico (gestor)** ✅ `/historico-equipe` — **conferida**,
      5 divergências. Falta a variante do coordenador (SCR-0028).
      `coordenador/screenshots/historico-equipe.png` ·
      `gestor/screenshots/historico-equipe.png` (+ `-2`)

- [x] **SCR-0027 / 0031 · Feedbacks Pendentes (coordenador / gestor)** ✅
      `/feedbacks-pendentes` — **feita em 06/09/2026**
      `coordenador/screenshots/feedbacks-pendentes.png` ·
      `gestor/screenshots/feedbacks-pendentes.png`
      *Correção do roteiro*: esta tela **não** é `/meus-feedbacks`. O legado diz
      "Feedbacks que **sua equipe** ainda precisa enviar no ciclo atual" — é a visão do
      gestor sobre a equipe, e a rota nova é a que responde isso.

- [x] **SCR-0029 · Início (gestor)** ✅ `/` — **conferida**, 4 divergências.
      Faltam as variantes de coordenador (SCR-0025) e colaborador (SCR-0033).
      `coordenador/screenshots/inicio.png` · `gestor/screenshots/inicio.png` (+ `-2`) ·
      `colaborador/screenshots/inicio.png` (+ `-2`, `-3`)
      *Atenção*: quatro telas do legado viraram uma. Entre com cada papel.

## Feedback

- [x] **SCR-0020 · Meus Feedbacks** ✅ `/meus-feedbacks` — **conferida**, 5 divergências
      `feedback/screenshots/meus-feedbacks.png` · `meus-feedbacks-colaborador.png` ·
      `meus-feedbacks-gestor.png`

- [x] **SCR-0019 · Minhas Anotações** ✅ `/anotacoes` — **conferida**, 1 divergência
      `feedback/screenshots/minhas-anotacoes.png`

- [ ] **SCR-0004 · Anotações Realizadas** ✅ `/anotacoes` (seção inferior)
      `admin/screenshots/anotacoes-realizadas.png` (+ `-2`)
      *Atenção*: no legado eram duas entradas de menu; aqui é uma tela com as duas
      partes.

- [ ] **SCR-0021 · Meu Histórico** ❌ **não implementada**
      `feedback/screenshots/meu-historico.png` · `meu-historico-colaborador.png` ·
      `meu-historico-gestor.png`
      É o histórico da **própria pessoa** — existe o da equipe, não o individual.

- [ ] **SCR-0022 · Caderno do Ciclo** ⚠️ parcial — `/anotacoes` cobre o conteúdo
      `feedback/screenshots/caderno-do-ciclo-painel.png` · `caderno-do-ciclo-widget.png`
      Falta o **botão flutuante** presente em todas as telas autenticadas.

- [x] **SCR-0023 · Modal Dar Feedback Livre** ⚠️ **parcial** — existe em `/minha-equipe`
      `feedback/screenshots/dar-feedback-livre-modal.png` (+ `-2`)
      O formulário foi feito junto com as ações de #59: três campos, anônimo e sensível.
      Falta só a entrada pelo banner do Início, que no legado oferecia a ação a todo
      mundo e não só a quem tem equipe (#8).

## Cliente e relatórios

- [ ] **SCR-0034 · Avaliações de Clientes** ✅ `/avaliacoes-clientes`
      `colaborador/screenshots/avaliacoes-clientes.png` ·
      `solicitar-avaliacao-modal.png` (+ `-2`)

- [ ] **SCR-0016 · Relatórios — Dados e Filtros** ✅ `/relatorios`
      `reports/screenshots/relatorios-dados-filtros.png` (+ `-2`)
      *Atenção*: confira os limites de linha (preview 50, tabela 100) e os filtros.

- [ ] **SCR-0017 · Emitir Relatório** ⚠️ parcial — `/relatorios` (seção Exportações)
      `reports/screenshots/emitir-relatorio.png`
      O legado tinha tela própria; aqui é uma seção. Confira se os campos de escopo do
      relatório executivo estão todos presentes.

- [x] **SCR-0035 · Fluxo Público do Cliente** ✅ **conferida em 02/09/2026** —
      `/avaliacao/{token}` · `docs/reversa/public/screenshots/` (17 capturas)
      A tela foi **refeita como wizard**: a divergência estrutural não existe mais. Cada
      etapa foi comparada com sua captura, inclusive a barra de progresso, que reproduz a
      escala de seis casas do legado (identificação 1/6, motivação/ramo/transição 2/6,
      perguntas interpolando de 3/6 a 4/6, tipo de serviço 5/6; capa e agradecimento sem
      barra).
      *Sobra para conferir com o cliente*, e nenhum destes se decide por screenshot:
      **(a)** a etapa Q6 nunca foi capturada — aqui ela é uma pergunta `nps` do formulário,
      conforme a hipótese de SCR-0044; **(b)** qual pergunta alimenta `overall_rating` nos
      relatórios (DEV-A12 assume a primeira de tipo `rating`); **(c)** o chip "+ Outro…" do
      tipo de serviço não existe, porque o contrato não aceita texto livre (DEV-A13).

## Sessão

- [x] **SCR-0001 · Login** ✅ `/login` — **conferida**, 6 divergências;
      ver `conferencia-resultado.md`
      `docs/reversa/auth/screenshots/login.png`

- [ ] **SCR-0002 · Meu Perfil** ✅ `/meu-perfil`
      `auth/screenshots/meu-perfil.png`

---

## Resumo antes de começar

| | |
|---|---|
| Telas literais a conferir | 18 (uma, a Agenda, está fora do corte) |
| Já conferidas | 17 — Administração inteira, e metade de Equipe/Feedback |
| Faltam | variantes de coordenador e colaborador, anotações realizadas, Cliente/Relatórios |
| Resultado até aqui | [`conferencia-resultado.md`](conferencia-resultado.md) — 76 divergências e 5 defeitos próprios |
| Já sabidamente ausentes | SCR-0021 (Meu Histórico), SCR-0023 (Feedback Livre) |
| Parciais | SCR-0017 (Emitir Relatório), SCR-0022 (Caderno do Ciclo) |
| Divergência estrutural | nenhuma em aberto |

As **8 telas modernizadas** (SCR-0036 a SCR-0044) não entram nesta conferência: por
decisão do modo híbrido elas não têm oráculo visual, e a paridade delas é semântica —
verificada em `parity_specs.md`, não por comparação de imagem.

Conferi tudo? O resultado vai para `screen_deviation_log.md`, e as divergências que
sobrarem viram fila de trabalho.
