# Conferência contra o oráculo — resultado

> O que saiu de comparar as telas do sistema novo com os screenshots do legado, seguindo
> o roteiro de [`conferencia-oraculo.md`](conferencia-oraculo.md).
>
> Este arquivo é o retorno da conferência: uma seção por tela conferida, com o que
> diverge e o que fazer. Telas ainda não conferidas simplesmente não aparecem aqui.
>
> **Como o roteiro manda ler**, em ordem de importância: texto (o modo literal exige
> diff zero), colunas e campos presentes, ações disponíveis, e por fim posicionamento.
> Cor e espaçamento vêm dos tokens e divergem por construção.

## Andamento

| | |
|---|---|
| Conferidas | 11 de 35 — todo o bloco de Administração, mais SCR-0035 e SCR-0001 |
| Defeitos próprios encontrados | 2 (um deles bloqueava a conferência; ambos corrigidos) |
| Divergências contra o oráculo | 53 registradas abaixo |

O bloco de Administração está **fechado**: SCR-0003, 0007, 0008, 0009, 0010, 0011, 0012,
0013, 0015, 0018 e 0024. Faltam os blocos de Equipe, Feedback e Cliente/Relatórios.

O ambiente usado é o do `deploy/seed_demo.py`: sem dados de verdade a conferência
marcaria caixa sem provar nada — tabela vazia esconde coluna, filtro e badge.

---

## Defeitos do sistema novo, achados ao rodar

Não são divergências contra o oráculo: são erros que só aparecem com o sistema de pé, a
mesma classe que a seção "Coisas que só aparecem rodando" de `estado-do-projeto.md`
descreve. Os dois foram corrigidos nesta rodada.

### BUG-01 — recarregar qualquer tela derrubava a sessão ⛔ *corrigido*

**Sintoma**: abrir uma rota autenticada diretamente, ou dar F5, voltava para o login.
Isso bloqueava a conferência inteira: não dá para percorrer 34 telas se navegar desloga.

**Causa**, nos dois lados:

- **Front**: no boot, `ProvedorDeSessao.carregar()` dispara `/auth/me` e `/settings` em
  paralelo. Depois de um reload o access token não existe (ele vive só em memória, por
  desenho), então os dois tomam 401 juntos e **cada um renova por conta própria, com o
  mesmo refresh token**.
- **API**: `refresh_session` lia `used_at`, decidia e só então gravava. Duas renovações
  que se cruzassem liam `NULL` juntas e **ambas passavam** — e a que chegasse um pouco
  depois, já com `used_at` gravado, era lida como reúso e revogava todas as sessões do
  usuário.

Ou seja: o front provocava, em todo carregamento de página, exatamente o cenário que o
detector de reúso existe para punir.

**Correção**: `api.ts` passa a compartilhar uma única renovação em curso entre todos os
chamadores; e `AuthRepository.reivindicar_refresh_token` rotaciona com um UPDATE
condicional (`SET used_at = now() WHERE digest = … AND used_at IS NULL`), o mesmo padrão
de reivindicação atômica que a submissão pública já usava. Quem perde a disputa é reúso
de verdade.

**O ganho de segurança é maior que o de usabilidade**: antes, duas apresentações
simultâneas de um token roubado passavam as duas — o detector ficava mudo justamente no
caso em que existe para falar. Coberto por
`test_renovacoes_simultaneas_nao_passam_as_duas`, e verificado contra a API de pé (duas
renovações concorrentes: `200` e `401`, onde antes eram `200` e `200`).

### BUG-02 — a lista de pessoas descrevia departamentos *corrigido*

`/admin/usuarios`, cartão "Pessoas": a descrição era
`${departamentos.length} departamento(s) cadastrado(s).` — texto de outra tela, colado
sobre a lista de gente. Passou a contar pessoas.

---

## SCR-0001 · Login

Rota `/login` · oráculo `auth/screenshots/login.png`

| # | Divergência | Peso |
|---|---|---|
| 1 | Subtítulo: legado "PLATAFORMA DE FEEDBACK INTERNO", novo "Entre para continuar" | texto — o modo literal pede diff zero |
| 2 | Logo do escritório ausente | conteúdo |
| 3 | Sem placeholders (`seu@email.com` e a senha mascarada existiam no legado) | texto |
| 4 | Sem o botão de revelar a senha (ícone de olho) | ação |
| 5 | "Esqueci minha senha" (link) virou "Esqueceu a senha? Fale com o administrador do escritório." | texto **e** função |
| 6 | Rótulos ganharam `*` de obrigatório, que o legado não tinha | texto |

A #5 não é escolha de redação: o link do legado leva ao reset de senha, que é a SCR-0038
do subset modernizado e ainda não existe. O texto de hoje é honesto, mas some quando a
tela de reset entrar — **os dois itens andam juntos**.

O fundo escuro do legado contra o claro do novo **não** entra na lista: é o design system
aplicado, e o roteiro exclui cor por construção.

## SCR-0003 · Painel Administrativo

Rota `/` (admin) · oráculo `admin/screenshots/dashboard.png` (+ `-2`)

| # | Divergência | Peso |
|---|---|---|
| 7 | Título: legado "Painel Administrativo", novo "Olá, Helena" | texto |
| 8 | Banner "💬 Dar Feedback para alguém" ausente | ação — é a entrada da SCR-0023, já sabidamente não implementada |
| 9 | Cards: legado tem **Usuários Ativos, Ciclo Atual, Taxa de Conclusão, Pendências**; novo tem **Concluídos, Pendentes, Atrasados, Fora da conta** | conteúdo — quatro métricas diferentes, não quatro rótulos diferentes |
| 10 | Seção "Conclusão por Departamento" (barras) ausente | conteúdo |
| 11 | Seção "Atividade no Ciclo Atual" ausente | conteúdo |
| 12 | Seção "Status dos Usuários" (rosca ativo/inativo) ausente | conteúdo |
| 13 | Seção "Resumo Geral" (total de feedbacks, enviados) ausente | conteúdo |

Esta é a maior divergência de conteúdo do subset literal depois da SCR-0035. As quatro
seções que faltam são o painel inteiro abaixo dos cards — o novo termina onde o legado
começa a mostrar agregados.

Chama a atenção a #9: as métricas do novo descrevem **pedidos do ciclo**, e as do legado
descrevem **o escritório**. Não é a mesma pergunta sendo respondida com outro rótulo.

## SCR-0007 · Usuários

Rota `/admin/usuarios` · oráculo `admin/screenshots/usuarios.png`

| # | Divergência | Peso |
|---|---|---|
| 14 | Colunas ausentes: **E-mail**, **Departamento** (com "+N" para múltiplos) e **Status** | conteúdo |
| 15 | Sem os filtros **Todos Departamentos / Todos Papéis / Todos Status** | ação |
| 16 | Sem **Exportar Excel** | ação |
| 17 | Sem ordenação por coluna (o legado ordena por Nome, E-mail, Cargo, Departamento, Papel, Status) | ação |
| 18 | O selo de papel é renderizado na coluna **Ações**, ao lado de "Remover"; a coluna "Capacidades" tem só o link "Editar" | posicionamento |

A #14 dói mais do que parece: sem **Status** a tela não distingue quem foi desligado, e o
soft-delete de BR-MIGRAR-018 fica invisível. Sem **Departamento**, some a informação que
o legado até paginava com "+8".

O modal virando formulário na própria página é esperado — o roteiro avisa.

## SCR-0008 · Departamentos

Rota `/admin/departamentos` · oráculo `admin/screenshots/departamentos.png`

| # | Divergência | Peso |
|---|---|---|
| 19 | Coluna **Descrição** ausente | conteúdo — e vai fundo: `departments` não tem a coluna no schema novo |
| 20 | Sem **Exportar Excel** | ação |
| 21 | Sem o download por linha (ícone em cada departamento) | ação |
| 22 | "Editar" virou "Renomear" | texto |

O novo ganhou uma coluna **Pessoas** que o legado não tinha. Adição, não perda — mas
entra na lista porque o modo literal compara nos dois sentidos.

A #19 é a única desta tela que não se resolve no front: exige coluna nova em
`departments` e migration.

## SCR-0009 · Ciclos de Feedback

Rota `/admin/ciclos` · oráculo `admin/screenshots/ciclos.png`

| # | Divergência | Peso |
|---|---|---|
| 23 | Coluna **Formulário** ausente — não dá para saber que formulário o ciclo usa | conteúdo |
| 24 | Sem **Editar** ciclo | ação |
| 25 | Sem **Arquivar** ciclo, e sem o filtro "Arquivados (N)" | ação — `status='archived'` existe no CHECK do banco e nenhuma tela o alcança |
| 26 | Início e Fim viraram uma coluna "Período" (o legado ordena por cada uma) | posicionamento |
| 27 | Descrição da página: o legado explica o que é um ciclo, o novo explica o efeito de abrir | texto |

O novo tem **Regerar pedidos**, que o legado não tem. O wizard de 3 passos do "Novo
Ciclo" virou formulário inline — esperado pelo padrão adotado, e os passos 2 e 3 nunca
foram capturados (LACUNA registrada em `admin/screens.md`).

A #25 é a que mais incomoda: existe um estado no banco que nenhuma tela produz nem mostra.

## SCR-0010 · Permissões de Feedback

Rota `/admin/permissoes` · oráculo `admin/screenshots/permissoes.png`

**Divergência estrutural.** O legado agrupa por avaliador — cada pessoa é uma linha
expansível, com avatar de iniciais, badge "N ativas" e exportação CSV própria. O novo é
uma tabela plana, uma linha por par.

| # | Divergência | Peso |
|---|---|---|
| 28 | Agrupamento por avaliador (acordeão) → tabela plana de pares | estrutural |
| 29 | Sem **Importar em Massa** | ação — o roteiro já avisava |
| 30 | Sem **Exportar CSV**, nem global nem por pessoa | ação |
| 31 | Sem ordenação **A-Z** | ação |
| 32 | Faltam os filtros por **tipo**, **status** e **ciclo** (o novo só filtra por nome) | ação |
| 33 | Sem avatar de iniciais nem badge "N ativas" por pessoa | posicionamento |

Com as 16 permissões do ambiente de demonstração a tabela plana passa; com as centenas
que o oráculo sugere, ela deixa de ser navegável. É a divergência com maior risco de
virar reclamação na homologação.

## SCR-0011 · Diagnóstico de Permissões

Rota `/admin/diagnostico` · oráculo `admin/screenshots/diagnostico.png` (+ `-2`, `-3`, `-4`)

Sem divergência material encontrada. As cinco categorias estão lá com o mesmo recorte
(sem pedido no ciclo, par recíproco faltando, sem cobertura, com usuário inativo, poucos
avaliadores/avaliados), mais os quatro cards de topo e a ação em massa "Criar pedidos
faltantes". É a tela mais densa do legado e a que melhor sobreviveu.

Foi conferida com a matriz suja de propósito do `seed_demo.py` — com matriz limpa ela
renderiza cinco seções vazias e não há o que comparar.

## SCR-0012 · Auditoria

Rota `/admin/auditoria` · oráculo `admin/screenshots/auditoria.png`

| # | Divergência | Peso |
|---|---|---|
| 34 | Sem **Exportar CSV (N)** | ação |
| 35 | Faltam os 4 cards: Ações hoje, Últimos 7 dias, **Ações sensíveis (7d)**, pessoa mais ativa | conteúdo |
| 36 | Falta o gráfico **"Atividade — últimos 14 dias"**, com legenda Normal/Sensível | conteúdo |
| 37 | Falta a seção colapsável **"Usuários Removidos (N)"** | conteúdo |
| 38 | Falta a contagem total nos títulos ("Logs de Auditoria (500)") | texto |
| 39 | Os detalhes aparecem como **JSON cru** | posicionamento |
| 40 | Descrição: "Registro completo de todas as ações realizadas no sistema" → "Registro permanente de ações sensíveis. Não pode ser editado nem apagado." | texto |

As #35 e #36 dependem de um conceito que o schema novo não tem: **ação sensível**.
`audit_logs` não distingue, então os dois cards e a legenda do gráfico não têm de onde
sair. É decisão de modelo, não de tela.

## SCR-0013 · Fale Conosco (triagem)

Rota `/admin/contatos` · oráculo `admin/screenshots/fale-conosco.png`

| # | Divergência | Peso |
|---|---|---|
| 41 | Tabela (Data, Contato, E-mail, Tipo, Status, Ações) → lista de cartões com abas | estrutural |
| 42 | Sem o filtro por **tipo** (o novo filtra só por status) | ação |
| 43 | Sem a ação **Ver** — o novo mostra a mensagem inline | ação, provavelmente para melhor |
| 44 | `contact_messages.type` é **texto livre**, sem catálogo: nada garante o par Sugestão/Crítica do legado | modelo |

A #44 apareceu por acidente e vale mais que as outras três. A primeira versão do
`seed_demo.py` inventou os tipos "suporte" e "comercial", e o sistema aceitou sem
reclamar — o legado só mostra **Sugestão** e **Crítica**. O seed foi corrigido para o
vocabulário do oráculo, mas o schema segue aceitando qualquer string, e a triagem não tem
como oferecer o filtro de tipo enquanto não houver catálogo.

## SCR-0015 · Central de Atualizações

Rota `/admin/atualizacoes` · oráculo `admin/screenshots/atualizacoes.png`

Sem divergência material encontrada. Rascunho e publicado, contagem de notificados, ação
de publicar e criação inline — tudo presente.

## SCR-0018 · Formulários

Rota `/admin/formularios` · oráculo `feedback/screenshots/formularios.png`

| # | Divergência | Peso |
|---|---|---|
| 45 | Falta a aba **"Formulários de Cliente Externo"** — o novo só administra os 360 | conteúdo, **grave** |
| 46 | Coluna **Descrição** ausente (`feedback_forms.description` existe no schema) | conteúdo |
| 47 | Sem **Editar** (nome e descrição) | ação |
| 48 | "Ativar/Desativar" virou "Arquivar" — nome e semântica diferentes | texto e função |

A #45 é a mais séria do bloco. As nove perguntas que o cliente responde no wizard público
saem de um formulário de cliente externo, e **hoje não há tela para editá-lo**: existe só
o editor de perguntas dos 360. Conecta com a SCR-0043 (Editor de Perguntas), do subset
modernizado, que a spec descreve atendendo aos dois tipos.

## SCR-0024 · Configurações

Rota `/admin/configuracoes` · oráculo `company-settings/screenshots/configuracoes.png`

| # | Divergência | Peso |
|---|---|---|
| 49 | **Upload de logo** (PNG/SVG, máx 2MB, com preview) virou um campo de texto "URL do logo" | função |
| 50 | Motivações e palavras-chave de calendário são editadas como **JSON cru**; o legado tem seção própria para as motivações | função |
| 51 | Falta "Última atualização: {data}" por configuração | conteúdo |
| 52 | Perdidos o agrupamento em cartões nomeados, os ícones, os tooltips (ⓘ) e o rótulo interno "Razão Social" | posicionamento |
| 53 | Cabeçalho: "Gerencie as configurações visuais e informações da empresa exibidas em todo o sistema" → "Valem para o escritório inteiro. Toggles nascem desligados." | texto |

A #50 não é questão de fidelidade e sim de quem usa a tela: pedir JSON válido a um
administrador de escritório é convite a erro de digitação que desliga um recurso em
silêncio. As três chaves extras de DEV-A09 aparecem como esperado.

---

## O que fazer com isto

Nada aqui foi decidido: divergência encontrada não é divergência aprovada. Cada linha
acima termina em uma de três saídas, e quem decide é o cliente na homologação:

1. **Implementar** — o legado tinha e faz falta (as seções do painel, as colunas e
   filtros de Usuários, o revelar-senha do login).
2. **Aprovar como deviation** — o novo é deliberadamente diferente; vai para
   `screen_deviation_log.md` com o motivo.
3. **Descartar** — o legado tinha e ninguém usava.

As que já têm dono claro: a #5 do login entra junto com a SCR-0038, a #8 do painel junto
com a SCR-0023, e a #45 dos formulários junto com a SCR-0043.

**Quatro não se resolvem no front** — mexem em schema, e por isso pedem decisão antes de
qualquer implementação:

- **#19** — `departments` não tem `description`.
- **#25** — `feedback_cycles.status` aceita `archived`, e nenhuma tela produz ou mostra
  esse estado.
- **#35/#36** — `audit_logs` não distingue ação sensível, então dois cards e a legenda do
  gráfico não têm de onde sair.
- **#44** — `contact_messages.type` é texto livre, sem catálogo.

E um padrão atravessa o bloco inteiro, mais barato de resolver de uma vez do que tela a
tela: **o legado exporta quase tudo** (Usuários, Departamentos, Permissões e Auditoria,
todos com Exportar Excel ou CSV) e **filtra quase tudo**. O sistema novo tem exportação
só em Relatórios. Se a decisão for implementar, um componente de exportação e outro de
filtro resolvem sete das divergências acima de uma vez — #16, #20, #21, #30, #34 e os
filtros de #15, #32 e #42.
