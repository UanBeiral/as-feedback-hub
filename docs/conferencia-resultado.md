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
| Conferidas | 17 de 35 |
| Defeitos próprios encontrados | 5 (um bloqueava a conferência; todos corrigidos) |
| Divergências contra o oráculo | 76 registradas abaixo |
| **Já resolvidas** | **36** — acompanhamento (15), exportação/filtros (12), as três decisões do cliente (8) e a tela de Feedbacks Pendentes |

O bloco de **Administração** está fechado (SCR-0003, 0007, 0008, 0009, 0010, 0011, 0012,
0013, 0015, 0018 e 0024) e o de **Equipe/Feedback** está a meio caminho (SCR-0029, 0030,
0032, 0020, 0027/0031 e 0019). Faltam o histórico e o início dos outros papéis, as
anotações realizadas, e o bloco de Cliente/Relatórios.

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

### BUG-03 — "Meus Feedbacks" não dizia sobre quem era cada pedido ⛔ *corrigido*

A tabela tinha Status, Prazo e "Enviado em". Nada mais. Com quatro pedidos do mesmo ciclo
a tela mostrava **quatro linhas idênticas**, e a pessoa não tinha como saber qual
responder — a tela era inutilizável, não incompleta. O mesmo valia no Início, onde cada
pendência aparecia como "Feedback sobre um colega".

A raiz estava no contrato: `RequestOut` devolvia `giver_id` e `receiver_id` como UUID e
nenhum nome. O front não tinha o dado para mostrar, e a saída óbvia — pedir `/profiles`
inteiro só para traduzir uuid em nome — é pior que resolver na origem.

`RequestOut` ganhou `giver_name` e `receiver_name`, resolvidos por **uma** consulta para
a lista toda (o conjunto de ids colapsa as repetições antes de ir ao banco). A tabela
ganhou a coluna **Avaliado**, como primeira; o Início passou a dizer o nome.

Que o oráculo tem uma busca chamada **"Buscar avaliado…"** é a confirmação de que o
legado sempre mostrou esse nome.

### BUG-04 — status cru, em inglês, na tela de Minha Equipe

`/minha-equipe` mostra a coluna Status com o valor do banco: `active`, minúsculo e em
inglês, numa tela em português onde todo o resto é traduzido. O legado usa um badge
"Ativo". Registrado junto da divergência #58, que reescreve a coluna de qualquer jeito.

### BUG-05 — o gestor aparece na própria equipe

`/minha-equipe` lista Marina Duarte entre os membros da equipe de Marina Duarte. No
oráculo o gestor não aparece na própria lista, e o rodapé "Total de membros na equipe"
conta sem ele. Registrado junto de #58.

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

## SCR-0029 · Início (Gestor)

Rota `/` como gestor · oráculo `gestor/screenshots/inicio.png`

| # | Divergência | Peso |
|---|---|---|
| 54 | Falta a **data por extenso** sob a saudação ("Sexta-Feira, 28 De Agosto De 2026") | texto |
| 55 | Falta o cartão **"Minhas Anotações"**, com "+ Anotar" e estado vazio próprio, direto no Início | conteúdo |
| 56 | Cards: legado tem **Membros da Equipe, Pendências, Taxa de Conclusão, Ciclo Atual**; novo repete os quatro do painel admin | conteúdo — a mesma troca de pergunta da #9 |
| 57 | Badge de papel: legado mostra **"Gestor (Admin)"**, o papel efetivo e o real juntos; o novo mostra só "Gestor" | texto |

O banner "Dar Feedback para alguém" também falta aqui — é a mesma #8, e aparece em todo
Início do legado, não só no do admin.

A #57 tem consequência prática: o seletor "Ver como…" troca o papel ativo (BR-MIGRAR-016)
e nada na tela lembra qual é o papel de verdade da pessoa.

## SCR-0030 · Minha Equipe (Gestor)

Rota `/minha-equipe` · oráculo `gestor/screenshots/minha-equipe.png`

**Divergência estrutural.** No legado esta tela é um **painel de acompanhamento do ciclo**;
no novo é uma listagem de pessoas.

| # | Divergência | Peso |
|---|---|---|
| 58 | Faltam as colunas **Pendentes de Enviar**, **Enviados**, **Pendentes de Leitura** e **Progresso** (barra + %) | conteúdo — é o miolo da tela |
| 59 | Faltam as três ações por membro: dar feedback, enviar lembrete, remover | ação |
| 60 | Sem **Exportar Excel** e sem **+ Adicionar Membro** | ação |
| 61 | Falta o rodapé: "Progresso geral da equipe", "N de M feedbacks enviados (%)" e "Total de membros na equipe: N" | conteúdo |
| 62 | Status aparece como `active` cru, sem badge (BUG-04) | texto |
| 63 | O próprio gestor entra na lista da própria equipe (BUG-05) | conteúdo |
| 64 | Descrição: o legado explica o recorte ("…no ciclo de feedback 360° atual. Feedbacks livres e de clientes são exibidos em outras seções") | texto |

O **lembrete por membro** (#59) é a única ação do legado sem correspondente em lugar
nenhum do sistema novo — as outras duas existem noutras telas.

## SCR-0032 · Histórico da Equipe (Gestor)

Rota `/historico-equipe` · oráculo `gestor/screenshots/historico-equipe.png`

| # | Divergência | Peso |
|---|---|---|
| 65 | O feedback livre aparece com os três campos **concatenados por " · "** numa linha; o legado rotula **Pontos Positivos**, **Pontos de Melhoria** e **Mensagem** separadamente | conteúdo |
| 66 | Falta a marca de leitura: **"✅ Ciente em {data} por {pessoa}"** | conteúdo — `read_at`/`read_by` existem no schema e nenhum endpoint os preenche |
| 67 | Falta a ação **Ver Detalhes** | ação |
| 68 | Faltam a ordenação por data e a busca dentro de cada seção | ação |
| 69 | Seções colapsáveis por tipo → abas com contagem | posicionamento — equivalente, e o novo é mais direto |

A #65 apaga uma distinção que o formulário faz questão de manter: elogio e crítica viram
a mesma frase corrida. A #66 é a ponta visível de uma lacuna já registrada em
`estado-do-projeto.md` — o destinatário não tem como marcar ciência.

## SCR-0020 · Meus Feedbacks

Rota `/meus-feedbacks` · oráculo `feedback/screenshots/meus-feedbacks-gestor.png`

| # | Divergência | Peso |
|---|---|---|
| 70 | Faltam os 3 cards: **Precisam da sua atenção**, **Enviados com sucesso**, **Abdicados** | conteúdo |
| 71 | Falta **"Buscar avaliado…"**, o filtro de status e o toggle **"Só pendentes"** | ação |
| 72 | Faltam a ordenação **A-Z** / **Data** e o botão **"Mostrar cancelados"** | ação — e o novo já traz os cancelados misturados, sem como escondê-los |
| 73 | Falta a seção **"Feedback Livre — Enviados por mim (N)"** | conteúdo |
| 74 | Descrição: "Gerencie seus feedbacks pendentes, enviados e abdicados" → "O que você precisa responder e o que já enviou neste ciclo" | texto |

A coluna do avaliado, que faltava, virou BUG-03 e já está corrigida — não entra como
divergência porque não era escolha, era defeito.

## SCR-0027 / SCR-0031 · Feedbacks Pendentes (coordenador / gestor)

Oráculo `gestor/screenshots/feedbacks-pendentes.png`

**O roteiro aponta a rota errada.** Ele manda conferir em `/meus-feedbacks`, mas o legado
diz, na própria descrição da tela: *"Feedbacks que **sua equipe** ainda precisa enviar no
ciclo atual."* É a visão do gestor **sobre a equipe**, não sobre si — outra tela, outro
escopo.

| # | Divergência | Peso |
|---|---|---|
| 75 | A tela **não existia** no sistema novo | conteúdo, **grave** — ✅ **feita em 06/09/2026** |

Some junto com a #58: as duas eram como o gestor acompanhava quem estava atrasado.

**Resolvida.** A tela nasceu em `/feedbacks-pendentes`, com `GET /team/pending`. Foi a
decisão do cliente de 06/09: a coluna "A enviar" de Minha equipe responde *quanto*, e a
lista responde *o quê* — "Diego deve o feedback sobre a Bruna, com prazo 15/09". Com
quatro pessoas dá no mesmo; com trinta, é a lista que permite cobrar item a item.

Quem está olhando sai da lista, e sai **na consulta**, não peneirado depois: o que o
gestor deve tem tela própria, e misturar faria ele cobrar a si mesmo no meio da equipe.
O "Lembrar" de cada linha reaproveita o endpoint de #59 — é por pessoa, não por pedido,
porque um aviso por linha encheria o sino de quem já sabe que está devendo.

Corrigir o roteiro fez parte do resultado: `conferencia-oraculo.md` mandava conferir em
`/meus-feedbacks`, que é outra tela e outro escopo.

## SCR-0019 · Minhas Anotações

Rota `/anotacoes` · oráculo `feedback/screenshots/minhas-anotacoes.png`

| # | Divergência | Peso |
|---|---|---|
| 76 | Faltam os cards **Total de anotações** e **Pessoas anotadas**, e a **busca por nome** | conteúdo |

O legado organiza as anotações **por ciclo e pessoa**; o novo lista em ordem cronológica.
Com três anotações dá na mesma; com um ciclo inteiro, não. O formulário inline no lugar
do modal "+ Nova Anotação" é o padrão já adotado em todo o sistema novo.

---

## Resolvidas — telas de acompanhamento restauradas

Frente escolhida em 06/09/2026, depois que a conferência mostrou que a mesma decisão se
repetia em quatro telas: **o que no legado era acompanhamento virou listagem**. Fecha as
divergências #9, #10, #11, #12, #13, #54, #55, #56, #58, #61, #62, #63, #70 e #74, mais
os defeitos BUG-04 e BUG-05.

Duas escolhas de fundo valem registro.

**Um endpoint por tela, não cinco chamadas.** `GET /dashboard` e `GET /team/progress`
montam cada painel de uma vez. A alternativa — o front pedir ciclo, progresso, perfis,
departamentos e atividade em paralelo — deixaria a primeira tela que todo mundo abre
esperando pela mais lenta das cinco.

**Todo número novo sai do mesmo denominador** de `CycleProgressService`: `cancelled` e
`waived` fora, `submitted` como concluído (BR-MIGRAR-009). Foi o legado ter três contas
divergentes que criou a regra, e um painel com conta própria a quebraria na tela mais
visível do sistema.

### O que mudou em cada tela

**Minha equipe** deixou de listar nomes e voltou a acompanhar. Ganhou as colunas
**A enviar**, **Enviados**, **A ler** e **Progresso**, o rodapé com progresso geral e
"Total de membros na equipe", o selo de status traduzido, e parou de incluir quem está
olhando na própria lista.

As duas contagens são separadas de propósito, como no legado: "a enviar" é o que a pessoa
deve escrever, "a ler" é o que escreveram sobre ela e ela não viu. Num número só, quem já
fez a parte dele e apenas não leu ficaria escondido atrás de quem não fez nada.

Quem não tem pedido no ciclo mostra **"fora do ciclo"** em vez de barra cheia. O serviço
trata "0 de 0" como 100% para não dividir por zero — mas na tabela, ao lado de quem tem
trabalho de verdade, a barra cheia leria como "está ótimo" quando o caso é outro.

**Meus feedbacks** ganhou os três cartões — Precisam da sua atenção, Enviados com
sucesso, Abdicados. Contados no cliente sobre a lista que já veio inteira: o que a tela
mostra e o que ela soma são a mesma coisa, e não duas verdades que podem divergir.

**Início** ganhou a data por extenso, os quatro cartões do legado (Pessoas ativas, Ciclo
atual, Taxa de conclusão, Pendências), o cartão "Minhas anotações" com total e pessoas
anotadas, e as quatro seções que faltavam: **Conclusão por departamento**, **Atividade no
ciclo atual**, **Status das pessoas** e **Resumo geral**.

Os quatro cartões antigos (Concluídos / Pendentes / Atrasados / Fora da conta) **ficaram**,
agora abaixo, no cartão do ciclo. Eles são mais precisos que os do legado e ninguém pediu
para tirá-los — a divergência #9 era sobre o que faltava, não sobre o que sobrava.

**Sobre os gráficos**: o legado usa barras verticais e uma rosca, com biblioteca de
gráfico. Aqui são barras horizontais feitas com `div`. Os dados destas telas cabem em
menos de dez linhas, a leitura horizontal acomoda nome longo de departamento sem girar
texto, e uma dependência de gráfico é peso que só se paga quando há gráfico de verdade a
desenhar. **Divergência de forma, deliberada** — o conteúdo é o mesmo.

### #59 — as três ações por membro

Feitas na mesma frente, depois de fechado o resto. Cada uma tinha um problema diferente.

**Dar feedback** não existia em tela nenhuma, embora `POST /free-feedbacks` estivesse
pronto desde sempre. Ganhou um formulário na própria página, com os três campos do legado
— pontos positivos, pontos de melhoria e mensagem —, mais anônimo e sensível.

Isso entrega, de passagem, a **SCR-0023** (Modal Dar Feedback Livre), que a conferência
listava como não implementada. Falta ainda a entrada pelo banner do Início (#8), que é
onde o legado a oferecia a todo mundo, e não só a quem tem equipe.

O aviso do anônimo é categórico de propósito: `giver_id` fica **nulo no banco**
(AMB-001), não escondido na serialização. Quem marca a caixa precisa saber que não há
volta — nem para a administração, nem para quem enviou.

**Enviar lembrete** não tinha endpoint em lugar nenhum, e era o único item do legado
nessa situação. Agora tem: `POST /team/{profile_id}/reminder` enfileira no outbox e o
worker vira notificação, com três regras que a spec não trazia escritas.

Só sai para quem tem pedido em aberto — cutucar quem já respondeu ensina a pessoa a
ignorar o sino, e por isso o botão nem aparece para quem está em dia. A chave de
idempotência inclui **o dia**, então dois cliques geram um aviso só e amanhã o gestor pode
insistir; sem o dia na chave, o segundo lembrete da semana sumiria em silêncio. E o
escopo é conferido por `TeamScopeService.assert_can_view`: cutucar alguém de fora da sua
equipe revelaria, pelo erro, que a pessoa existe.

Quando não há o que lembrar, a API devolve `pendentes: 0` e a tela diz "está em dia" em
vez de "enviado" — a diferença entre avisar e não ter o que avisar chega a quem clicou.

**Remover** ficou de fora para gestor e coordenador, **de propósito**. No sistema novo
tirar alguém da equipe é mexer na hierarquia (`PUT /profiles/{id}/manager`), e isso é ato
de admin/RH. O legado mostrava o X ao gestor; ampliar essa autorização é decisão do
cliente, não consequência de copiar um ícone. A ação aparece para quem já tem o poder —
admin e RH — e some para os demais.

### O que continua faltando nestas telas

- **#60** — Exportar Excel e Adicionar Membro, que entram na frente de exportação.
- **#71, #72, #73** — busca, filtros, ordenação e a seção de feedback livre enviado, em
  Meus feedbacks. Também da frente de exportação e filtros.
- **#8** — o banner "Dar Feedback para alguém" no Início. O formulário já existe; falta
  a porta de entrada para quem não tem equipe.
- **Decisão do cliente**: o gestor deve poder remover alguém da própria equipe?

---

## Resolvidas — exportação e filtros

Segunda frente, 06/09/2026. O legado exporta e filtra em quase toda tabela, e o sistema
novo só exportava em Relatórios. Fecha #14, #15, #16, #17, #20, #30, #31, #32, #42, #60,
#71 e #72 — doze divergências espalhadas por seis telas, com o mesmo par de peças.

### As peças

`lib/exportar.ts` monta o CSV e `lib/tabela.ts` guarda busca, filtros e ordenação num
hook. Três decisões dentro delas valem registro.

**A exportação é no navegador**, não no servidor. As exportações pesadas seguem sendo job
do worker (AD-07), porque montam dados que a tela não tem; estas são o oposto — a tabela
já está carregada, e mandá-la de volta para receber o que o navegador tem em memória seria
viagem sem propósito. E há um ganho que não é de latência: exportar da tela garante que o
arquivo é **o que a pessoa está vendo**, com os filtros aplicados. É o `reflects_filters`
que `target_screens.md` pede, e é o que um relatório gerado no servidor "com os mesmos
filtros" erra na primeira divergência entre as duas implementações.

**Célula que começa com `=`, `+`, `-` ou `@` é prefixada com aspa simples.** Excel e
LibreOffice tratam isso como fórmula: um departamento chamado "-Jurídico" viraria erro de
cálculo na planilha, e um campo livre viraria injeção de fórmula. Junto vai o BOM, sem o
qual o Excel em português abre o arquivo em Latin-1 e todo acento quebra.

**A ordenação usa `localeCompare` em pt-BR**, com `sensitivity: "base"` — é o que faz
"Ávila" cair entre "Avila" e "Azevedo" em vez de ir para o fim, que é onde a comparação
por código de caractere o coloca. Nulos vão sempre para o fim, nas duas direções: "sem
cargo" no topo da lista ordenada por cargo não ajuda ninguém.

**Filtrar no cliente não é o padrão para tudo.** Estas telas carregam a lista inteira
porque o escritório tem dezenas de pessoas, não milhares. Relatórios pagina no servidor
porque lá o volume é outro, e o dia em que uma destas tabelas passar de alguns milhares
de linhas, o certo é mover o filtro para a API — não aumentar o limite da consulta. Está
escrito no topo de `lib/tabela.ts`, onde quem for mexer vai ler.

### O que mudou em cada tela

**Usuários** ganhou as três colunas que faltavam — E-mail, Departamento e Status —, mais
os três filtros do oráculo, ordenação em seis colunas e exportação. Sem Status o
soft-delete de BR-MIGRAR-018 era invisível na tela; agora tem selo.

O e-mail exigiu mexer no contrato: mora em `users`, não em `profiles`. `ProfileSummary`
ganhou o campo, preenchido por uma junção pelo próprio id (`profiles.id` **é**
`users.id`, DEV-A03) numa consulta só para a lista toda.

**Permissões** trocou o campo de busca solto pelos três filtros do legado — tipo, situação
e ciclo —, com ordenação e exportação. Não resolve a #28 (o agrupamento por avaliador,
que é outra tela), mas torna a tabela plana navegável enquanto essa decisão não vem.

**Auditoria**, **Fale conosco**, **Departamentos**, **Minha equipe** e **Meus feedbacks**
ganharam busca, filtro, ordenação e exportação na mesma medida. Dois detalhes:

- Em Auditoria e Fale conosco o seletor lista **só os valores presentes**, não um catálogo
  fixo. Em Fale conosco isso é consequência direta da #44 — `type` é texto livre, não há
  catálogo de onde tirar as opções —, e oferecer filtro que não devolve nada é pior que
  não oferecer.
- Em Meus feedbacks o **"Só pendentes"** ficou como caixa própria, e não como mais uma
  opção do seletor de status: é a pergunta que a pessoa faz toda vez que abre a tela, e o
  oráculo também lhe dá um controle separado.

### O que continua faltando nestas telas

- **#21** — o download por linha em Departamentos. Um CSV de uma linha só; a exportação
  da tabela cobre o caso.
- **#28** — o agrupamento por avaliador em Permissões. É reescrever a tela, não filtrá-la.
- **#29** — Importar em Massa de permissões.
- **#34** — o botão traz a contagem (`Exportar CSV (3)`), mas os títulos das seções
  seguem sem o total, como no legado ("Logs de Auditoria (500)").
- **#60** — Adicionar Membro em Minha equipe. Depende de a decisão sobre remoção sair.
- **#73** — a seção "Feedback Livre — Enviados por mim" em Meus feedbacks.

---

## Resolvidas — as três decisões do cliente

Decididas em 06/09/2026, quando a conferência tinha isolado o que não se resolvia no
front. Fecham #19, #22, #34, #35, #36, #37, #38 e #59, e mexem em schema — daí a
migration `0006`.

### O gestor pode remover da própria equipe (#59)

**Sim**, e a autorização é do **vínculo, não do papel**. `DELETE /team/{profile_id}`
está aberta a qualquer sessão, e o serviço só remove se quem pede for o gestor direto ou
o coordenador daquela pessoa. Um `require_role("gestor")` seria mais frouxo, não mais
rígido: deixaria um gestor mexer na equipe de outro.

Ver alguém não dá direito de remover — um coordenador enxerga os liderados do próprio
gestor, porque o escopo é união (BR-MIGRAR-017), e não tem nada a decidir sobre eles.
Quem não é dono do vínculo recebe **404 e não 403**, pela mesma razão do detalhe de
request: o erro não confirma que o vínculo existe.

Quem é liderado **e** coordenado perde primeiro a liderança. Se sobrasse a coordenação, a
pessoa continuaria na equipe depois de "sair dela".

E não é exclusão: quem sai continua no escritório, com histórico e acesso intactos.
Desligar segue sendo `DELETE /profiles/{id}`, de admin/RH. A tela confirma antes, não
porque a ação seja destrutiva, mas porque é de mão única para quem clicou — desfazer
depende da administração refazer o vínculo.

### Departamento tem descrição (#19)

Coluna nova em `departments`, nulável: os departamentos migrados do legado não têm
descrição, e exigir uma agora obrigaria a inventar texto para dado que já existe. Entra
na tabela, no formulário de criação, na edição inline e na exportação.

O `PUT` manda o recurso inteiro, e descrição em branco **apaga** a anterior — não
"mantém a que estava". Tratar como "mantém" faria a única forma de apagar uma descrição
ser um `UPDATE` direto no banco.

### A auditoria distingue ação sensível (#34 a #38)

Coluna `is_sensitive`, **gravada no INSERT** a partir de um catálogo em código. Não é
derivação na consulta, e a diferença importa: derivar faria toda mudança futura no
catálogo reescrever a classificação do passado, e trilha append-only não reescreve o
passado.

A régua é **eleva ou remove poder, ou apaga trabalho já esperado**: trocar papel, mexer
em capacidades, redefinir a senha de outra pessoa, remover perfil e cancelar pedido. Fora
ficam cadastrar alguém, a pessoa trocar a própria senha, reativar quem voltou e as
movimentações de equipe — mexem em gente, mas são o fluxo cotidiano do escritório. É a
mesma razão pela qual o Diagnóstico deixa desequilíbrio de carga fora dos "pontos de
atenção": quando tudo é urgente, nada é.

A migration duplica o catálogo de propósito — migration não importa código de aplicação,
que muda embaixo dela — e o preço da duplicação é um teste que compara as duas listas.
Sem ele o backfill classificaria o passado com uma régua e o presente com outra.

Com isso a tela ganhou os quatro cartões (hoje, 7 dias, sensíveis em 7 dias, quem mais
agiu), o gráfico de 14 dias com as barras empilhadas e a legenda Normal/Sensível, e o
`GET /audit-logs/summary`, que é rota separada da listagem porque responde outra
pergunta: a listagem pagina o detalhe, o resumo agrega o todo.

O gráfico teve um defeito que só apareceu rodando: com altura em porcentagem e nenhuma
altura definida no pai flex, as barras resolviam para zero e o gráfico ficava vazio
**com dados**. Corrigido com `h-full` na coluna do dia.

### O que continua faltando

- **#37** — a seção "Usuários Removidos" da auditoria.
- **#21** — o download por linha em Departamentos.
- **#39, #40** — detalhes em JSON cru e o texto do cabeçalho.

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
