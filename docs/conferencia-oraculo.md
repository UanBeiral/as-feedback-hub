# Conferência contra o oráculo — 35 telas literais

> Roteiro para a validação que `parity_specs.md` exige e que nenhum teste automatizado
> substitui: comparar cada tela do sistema novo com o screenshot do legado.
>
> **Como usar**: suba o sistema (`README` § Rodando local), abra a rota numa aba e o
> screenshot noutra, e marque a caixa quando conferir. Divergência encontrada vai para
> `docs/reversa/migration/screen_deviation_log.md`, com o SCR e o que difere.
>
> O que olhar, em ordem de importância: **texto** (rótulos, mensagens, estados vazios —
> o modo literal exige diff zero), **colunas e campos** presentes, **ações** disponíveis,
> e por fim posicionamento. Cor e espaçamento vêm dos tokens e divergem por construção
> onde o design system foi aplicado.

Legenda: ✅ tela existe · ⚠️ existe parcialmente · ❌ não implementada

---

## Administração

- [ ] **SCR-0003 · Painel Administrativo** ✅ `/`
      `docs/reversa/admin/screenshots/dashboard.png` (+ `-2`, `-3`, `-4`)
      *Atenção*: no legado eram quatro telas de início por papel; aqui é uma rota só que
      se adapta. Confira se o conteúdo do admin bate — não o caminho.

- [ ] **SCR-0007 · Usuários** ✅ `/admin/usuarios`
      `admin/screenshots/usuarios.png` · `usuarios-modal-novo-usuario.png`
      *Atenção*: o modal virou formulário na própria página.

- [ ] **SCR-0008 · Departamentos** ✅ `/admin/departamentos`
      `admin/screenshots/departamentos.png` · `departamentos-modal-novo.png`

- [ ] **SCR-0009 · Ciclos de Feedback** ✅ `/admin/ciclos`
      `admin/screenshots/ciclos.png` · `ciclos-modal-novo.png` (+ `-2`, `-3`) ·
      `ciclos-modal-editar.png`

- [ ] **SCR-0010 · Permissões** ✅ `/admin/permissoes`
      `admin/screenshots/permissoes.png` · `permissoes-modal-nova.png`
      *Atenção*: o legado tinha importação em massa; a tela nova não tem.

- [ ] **SCR-0011 · Diagnóstico de Permissões** ✅ `/admin/diagnostico`
      `admin/screenshots/diagnostico.png` (+ `-2`, `-3`, `-4`)
      *Atenção*: é a tela mais densa do legado. Confira as **5 categorias**, o texto de
      cada banner explicativo e as ações em massa.

- [ ] **SCR-0012 · Auditoria** ✅ `/admin/auditoria`
      `admin/screenshots/auditoria.png` (+ `-2`, `-3`)

- [ ] **SCR-0013 · Fale Conosco (admin)** ✅ `/admin/contatos`
      `admin/screenshots/fale-conosco.png`

- [ ] **SCR-0015 · Central de Atualizações** ✅ `/admin/atualizacoes`
      `admin/screenshots/atualizacoes.png`

- [ ] **SCR-0024 · Configurações** ✅ `/admin/configuracoes`
      `docs/reversa/company-settings/screenshots/configuracoes.png`
      *Atenção*: o novo tem 11 chaves contra 8 do legado (DEV-A09). As três extras são
      esperadas.

- [ ] **SCR-0018 · Formulários** ✅ `/admin/formularios`
      `docs/reversa/feedback/screenshots/formularios.png` · `formularios-modal-novo.png`

- **SCR-0014 · Agenda** ❌ fora do corte por decisão (AMB-007, fase 2).
      `admin/screenshots/agenda.png` — não precisa conferir.

## Equipe

- [ ] **SCR-0005 · Minha Equipe (admin)** ✅ `/minha-equipe`
      `admin/screenshots/minha-equipe.png` · `minha-equipe-modal-adicionar-membro.png`

- [ ] **SCR-0006 · Histórico da Equipe (admin)** ✅ `/historico-equipe`
      `admin/screenshots/historico-equipe.png` (+ `-2`)
      *Atenção*: confira as **três seções** (livre, clientes, 360) e os filtros.

- [ ] **SCR-0026 / 0030 · Minha Equipe (coordenador / gestor)** ✅ `/minha-equipe`
      `coordenador/screenshots/minha-equipe.png` · `gestor/screenshots/minha-equipe.png`
      *Atenção*: é a mesma rota do admin, com escopo diferente. Entre com um gestor para
      conferir — o conteúdo muda, o layout não.

- [ ] **SCR-0028 / 0032 · Histórico (coordenador / gestor)** ✅ `/historico-equipe`
      `coordenador/screenshots/historico-equipe.png` ·
      `gestor/screenshots/historico-equipe.png` (+ `-2`)

- [ ] **SCR-0027 / 0031 · Feedbacks Pendentes (coordenador / gestor)** ✅ `/meus-feedbacks`
      `coordenador/screenshots/feedbacks-pendentes.png` ·
      `gestor/screenshots/feedbacks-pendentes.png`

- [ ] **SCR-0025 / 0029 / 0033 · Início (coordenador / gestor / colaborador)** ✅ `/`
      `coordenador/screenshots/inicio.png` · `gestor/screenshots/inicio.png` (+ `-2`) ·
      `colaborador/screenshots/inicio.png` (+ `-2`, `-3`)
      *Atenção*: quatro telas do legado viraram uma. Entre com cada papel.

## Feedback

- [ ] **SCR-0020 · Meus Feedbacks** ✅ `/meus-feedbacks`
      `feedback/screenshots/meus-feedbacks.png` · `meus-feedbacks-colaborador.png` ·
      `meus-feedbacks-gestor.png`

- [ ] **SCR-0019 · Minhas Anotações** ✅ `/anotacoes`
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

- [ ] **SCR-0023 · Modal Dar Feedback Livre** ❌ **não implementada**
      `feedback/screenshots/dar-feedback-livre-modal.png` (+ `-2`)
      A API existe (`POST /free-feedbacks`); a interface, não.

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

- [ ] **SCR-0035 · Fluxo Público do Cliente** ⚠️ **divergência estrutural conhecida**
      `docs/reversa/public/screenshots/` — 17 capturas do wizard
      O legado é um **wizard de 16 etapas** (boas-vindas → identificação → motivação com
      ramos → 9 perguntas → tipo de serviço → agradecimento). O novo é **página única**.
      Funciona e preserva as perguntas, mas a experiência é outra. Esta é a maior
      divergência do subset literal e precisa de decisão: ou vira deviation aprovada, ou
      a tela é refeita como wizard.

## Sessão

- [ ] **SCR-0001 · Login** ✅ `/login`
      `docs/reversa/auth/screenshots/login.png`

- [ ] **SCR-0002 · Meu Perfil** ✅ `/meu-perfil`
      `auth/screenshots/meu-perfil.png`

---

## Resumo antes de começar

| | |
|---|---|
| Telas literais a conferir | 35 (uma, a Agenda, está fora do corte) |
| Já sabidamente ausentes | SCR-0021 (Meu Histórico), SCR-0023 (Feedback Livre) |
| Parciais | SCR-0017 (Emitir Relatório), SCR-0022 (Caderno do Ciclo) |
| Divergência estrutural | SCR-0035 (wizard vs página única) |

As **8 telas modernizadas** (SCR-0036 a SCR-0044) não entram nesta conferência: por
decisão do modo híbrido elas não têm oráculo visual, e a paridade delas é semântica —
verificada em `parity_specs.md`, não por comparação de imagem.

Conferi tudo? O resultado vai para `screen_deviation_log.md`, e as divergências que
sobrarem viram fila de trabalho.
