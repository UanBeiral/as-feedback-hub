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
| **Já resolvidas** | **40** — acompanhamento (15), exportação/filtros (12), as decisões do cliente (8) e as telas que não existiam (5) |

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
| 45 | Falta a aba **"Formulários de Cliente Externo"** — o novo só administra os 360 | conteúdo, **grave** — ✅ **feita em 06/09/2026** |
| 46 | Coluna **Descrição** ausente (`feedback_forms.description` existe no schema) | conteúdo |
| 47 | Sem **Editar** (nome e descrição) | ação |
| 48 | "Ativar/Desativar" virou "Arquivar" — nome e semântica diferentes | texto e função |

A #45 era a mais séria do bloco, e **foi resolvida**. As nove perguntas que o cliente
responde no wizard público saem de um formulário de cliente externo, e até aqui elas só
existiam no banco: havia `GET/POST` de formulário e `POST` de pergunta, e nada para ler,
editar, remover ou reordenar. Mudar o questionário do escritório era abrir o Postgres.

A aba entrou com o editor inteiro, e com isso a **SCR-0043** também sai do papel. Duas
diferenças em relação à aba dos 360, e as duas vêm de o formulário ser respondido por
gente de fora:

- **Os tipos são outros**: estrelas 0–10, NPS e sim/não existem aqui e não lá, porque é o
  que o wizard público sabe desenhar. `multiple_choice` fica de fora mesmo aceito pelo
  contrato — não há onde cadastrar as opções, e oferecê-lo daria uma pergunta sem
  resposta possível.
- **Remover pode não apagar.** Pergunta já respondida é **arquivada**: sai dos formulários
  novos e continua explicando os relatórios antigos. Apagar destruiria a resposta de um
  cliente para limpar um formulário — e o FK de `client_eval_answers` recusaria de
  qualquer jeito, com um erro que não explica nada a quem clicou.

A coluna `is_active` (migration `0007`) é o que permite distinguir os dois "remover". A
tela avisa antes qual vai acontecer, porque a diferença muda o que a pessoa deve esperar.

Verificado rodando: a pergunta respondida virou arquivada com as respostas intactas, a
nunca respondida sumiu de vez, e o wizard público passou de 9 para 8 perguntas.

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

## SCR-0034 · Avaliações de Clientes

Rota `/avaliacoes-clientes` · oráculo `colaborador/screenshots/avaliacoes-clientes.png`

| # | Divergência | Peso |
|---|---|---|
| 77 | Faltam os cartões **Pendentes** e **Respondidas** | conteúdo |
| 78 | "Quem será avaliado" é um `select`; o legado tem **busca com resultado**, mostrando papel e um botão "Solicitar" por pessoa | ação — com 40 pessoas o select deixa de servir |
| 79 | Falta a seção **"Filtrar avaliações"** (profissional, cliente, WhatsApp, status, período) | ação |
| 80 | Falta a coluna **Profissional** — a lista não diz sobre quem é cada avaliação | conteúdo, **grave** |
| 81 | Descrição diverge do legado | texto |

A #80 é a mesma doença do BUG-03: uma lista de avaliações que não nomeia o avaliado.
Aqui não chega a inutilizar a tela, porque o nome do cliente identifica a linha — mas o
gestor não consegue ler "quantas avaliações a Bruna recebeu" sem abrir uma a uma.

O WhatsApp aparece **completo** e isso está certo: BR-MIGRAR-022 manda mascarar para quem
não é admin/RH, e a rota faz exatamente isso.

## SCR-0016 · Relatórios — Dados e Filtros

Rota `/relatorios` · oráculo `reports/screenshots/relatorios-dados-filtros.png`

| # | Divergência | Peso |
|---|---|---|
| 82 | Falta a aba **Livres** — o legado tem quatro (Clientes, Livres, 360°, Engajamento) | conteúdo |
| 83 | Faltam os filtros por aba (Nota, Motivação, Profissional, De, Até, Buscar cliente) | ação |
| 84 | Falta o botão **Colunas** (escolher o que aparece) | ação |
| 85 | Falta o **Preview** antes de exportar | ação |
| 86 | Falta o contador "N resultados" | conteúdo |
| 87 | Sem ordenação por coluna | ação |
| 88 | Descrição: "Gere relatórios personalizados com filtros, escolha de colunas e exportação em CSV" → "Os mesmos números que aparecem nos painéis" | texto |

#82 a #87 resolvidas — ver "Resolvidas — Relatórios" no fim.

## SCR-0002 · Meu Perfil

Rota `/meu-perfil` · oráculo `auth/screenshots/meu-perfil.png`

| # | Divergência | Peso |
|---|---|---|
| 89 | Falta o **Departamento** | conteúdo |
| 90 | "Dados Pessoais" virou "Dados" | texto |

O novo mostra WhatsApp e uma seção **Acesso** com as capacidades, que o legado não tem —
adição, e boa: é a única tela onde a pessoa descobre o que pode fazer.

## SCR-0004 · Anotações Realizadas

Rota `/anotacoes` (seção inferior) · oráculo `admin/screenshots/anotacoes-realizadas.png`

Sem divergência material além da #76, que vale para as duas seções. No legado eram duas
entradas de menu; aqui é uma tela com as duas partes, como o roteiro previa.

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

(Nada — #37, #21, #39 e #40 entraram nos lotes seguintes. Ver as seções
"Resolvidas" no fim do documento.)

---

## O que fazer com isto

Nada aqui foi decidido de véspera: divergência encontrada não é divergência aprovada.
Cada linha acima terminou em uma de três saídas —

1. **Implementada** — o legado tinha e fazia falta. É o caso de 87 das 90.
2. **Desvio deliberado** — o novo é diferente de propósito, e o motivo está registrado na
   seção "Resolvidas" correspondente: **#2** (logo no login), **#43** (a mensagem do Fale
   Conosco aparece inline, sem o modal "Ver") e **#67** ("Ver Detalhes" no histórico, pelo
   mesmo motivo).
3. **Descartada** — nenhuma.

**Quatro exigiam decisão de schema**, e as quatro foram tomadas em 06/09/2026 com o
cliente:

- **#19** — `departments` ganhou `description` (migration `0006`).
- **#25** — `archived` de `feedback_cycles` ganhou tela: arquivar, filtro e contagem.
- **#35/#36** — `audit_logs` ganhou `is_sensitive`, gravado no INSERT a partir de um
  catálogo em código (migration `0006`).
- **#44** — `contact_messages.type` virou catálogo de duas opções.

E o padrão que atravessava o bloco inteiro — **o legado exporta e filtra quase tudo, e o
novo só exportava em Relatórios** — foi resolvido de uma vez com `lib/exportar.ts` e
`lib/tabela.ts`, como previsto: fecharam #16, #20, #21, #30, #34 e os filtros de #15, #32
e #42 com o mesmo par de peças.

### Defeitos encontrados pelo caminho

A conferência não era para achar bug, e achou oito. Todos corrigidos:

| # | O que era |
|---|---|
| BUG-01 | recarregar a página deslogava — duas renovações simultâneas do mesmo refresh token |
| BUG-02 | contagem do sino divergindo da lista |
| BUG-03 | "Meus feedbacks" não dizia sobre quem era cada pedido |
| BUG-04 | status do membro aparecia como `active` cru |
| BUG-05 | o gestor entrava na lista da própria equipe |
| BUG-06 | o histórico mostrava feedback sensível, que a rota de recebidos esconde |
| BUG-07 | `can_view_team_history` decidia o menu sem que a rota a exigisse |
| BUG-08 | "Usuários removidos" renderizava duas vezes na Auditoria |

O BUG-01 e o BUG-07 são os que mais valeram a conferência: um derrubava a sessão de quem
recarregava a página, o outro deixava uma capacidade valendo só no menu.

## Resolvidas — Relatórios

06/09/2026. Fecha #82 a #87, e com elas a última tela que ainda tinha divergência de
ação.

### A aba Livres (#82)

O legado tem quatro abas e o novo tinha três: feedback livre não aparecia em relatório
nenhum. `GET /reports/free-feedbacks` agrega por pessoa, e a linha traz **recebidos e
enviados lado a lado** — a pergunta que o relatório responde é sobre reciprocidade
(BR-MIGRAR-002), e quem recebe muito sem escrever nada só se enxerga com as duas colunas
juntas.

São duas agregações com chaves diferentes (`receiver_id` e `giver_id`), casadas por id em
Python. Não cabem num `GROUP BY` só, e o custo é irrisório porque cada uma devolve uma
linha por pessoa, não por feedback.

**Anônimo conta para quem recebeu e para ninguém como remetente.** Não há autor no banco
(AMB-001); atribuí-lo a alguém na hora do relatório seria reinventar o autor que o
anonimato apagou de propósito.

### Uma aba só, quatro vezes (#83 a #87)

As quatro abas mostram a mesma coisa com dados diferentes: uma tabela agregada por pessoa.
Escritas à mão quatro vezes, foi o que fez a tela nascer sem filtro, sem ordenação e sem
contador — cada melhoria custava quatro edições, e por isso nenhuma acontecia. Agora é
`AbaDeRelatorio<T>`, e o que vale para uma vale para as quatro.

A coluna declara `valor` (o que ordena e o que vai para o CSV) e, quando o visual não é o
valor cru, `celula`. Separar os dois é o que impede o CSV de sair com `—` no lugar de
vazio, ou com uma barra de progresso virando `[object Object]`.

**Os filtros são de dois tipos, e a divisão não é arbitrária.** Ciclo, departamento e
período mudam *o que o servidor agrega* — filtrar depois daria média de gente que o filtro
devia ter tirado da conta. Busca e ordenação mexem só na apresentação das linhas já
agregadas, e por isso ficam no navegador. As rotas já aceitavam esses parâmetros desde o
começo; o que faltava era a tela oferecê-los.

O **Preview** (#85) sai das linhas já carregadas, não de uma segunda consulta: a tabela na
tela nasceu destes mesmos filtros, e perguntar de novo ao servidor só somaria a chance de
as duas respostas discordarem. Ele existe porque XLSX vira job no worker — sem prévia, o
erro de filtro só aparece no arquivo, minutos depois.

O **seletor de colunas** (#84) usa `details`/`summary`: abre, fecha ao clicar fora e é
navegável por teclado sem uma linha de JS. A coluna que identifica a linha é `fixa` e
aparece desabilitada em vez de sumir da lista — esconder o nome deixaria a tabela
ilegível, e omitir a caixa faria parecer que a coluna não existe.

### O filtro de período faltava no worker

Achado ao ligar os filtros: `POST /reports/exports` guardava `desde` e `ate`, e o job de
`client` os ignorava. O XLSX sairia com o relatório inteiro enquanto a tela mostrava o
período escolhido — a discordância exata que o Preview existe para evitar.

## Resolvidas — histórico, ciência e feedback livre enviado

06/09/2026. Fecha #66, #67, #68 e #73, e implementa **SCR-0021 · Meu Histórico**, a única
tela do oráculo que não existia no sistema novo.

### Meu Histórico é o histórico da equipe com escopo de um

`GET /reports/my-history` reusa `TeamHistoryQuery` com `{tenant.user_id}` no lugar do
escopo resolvido. Um segundo jeito de montar as mesmas três seções seria um segundo jeito
de elas discordarem — e discordar sobre o que uma pessoa recebeu é pior do que sobre um
total.

Na tela é o mesmo componente. O que existe só aqui é a **ciência** (#66): o botão aparece
no item ainda não lido, e o servidor recusa a marca de quem não é o destinatário. Avaliação
de cliente não tem botão — ela é *sobre* a pessoa, não *para* ela, e não há o que
reconhecer.

A marca agora diz **quem** deu ciência (`lido_por`, por `outerjoin` em `read_by`). Sem o
nome, "ciente em 12/03" no histórico da equipe deixava no ar se quem leu foi a pessoa ou a
administração.

### O sensível não podia estar ali (BUG-06)

Achado ao montar o Meu Histórico: `TeamHistoryQuery.livre` não filtrava `is_sensitive`. A
rota de recebidos esconde o sensível do destinatário desde sempre — invariante do
aggregate — e o histórico o mostrava, para o gestor e, se a tela existisse, para a própria
pessoa. Agora o padrão é esconder, e team-history só inclui para **admin/RH**, exatamente
como `/free-feedbacks/received`.

### A capacidade que ninguém cobrava (BUG-07)

`can_view_team_history` existia no perfil, aparecia na tela de usuários, decidia o menu — e
a rota `/reports/team-history` não a exigia. Capacidade que o servidor não cobra é
decoração: quem soubesse a URL entrava. Agora a rota exige (BR-MIGRAR-013/015), e o menu
deixou de oferecer por "tem equipe" — oferecer o que o servidor recusa é pior do que não
oferecer.

### Ordenação e busca por seção (#68)

Busca já existia; faltava a ordem. Agora há o alternador **Mais recentes / Mais antigos**, e
item sem data vai para o fim nas duas direções — "sem data" no topo de "mais antigos
primeiro" seria uma resposta errada para a pergunta que a ordem faz.

### Feedback livre enviado por mim (#73)

`GET /free-feedbacks/sent`, numa seção própria abaixo dos pedidos do ciclo. Separada
porque é outra coisa: em cima está o que o ciclo cobra de mim, com prazo e status; aqui, o
que escrevi por iniciativa própria e não tem pendência nenhuma. Junto, a soma "quanto
falta" mentiria.

**O que enviei anônimo não aparece**, e não é lacuna: anônimo não guarda autor (AMB-001), e
listá-lo como meu exigiria guardar exatamente o vínculo que o anonimato existe para não
guardar. A tela diz isso na descrição, em vez de deixar a pessoa contando os que faltam.

### #67 fica como desvio deliberado

"Ver Detalhes" abria um modal com o conteúdo que o novo já mostra inline, com os três
campos rotulados. Um clique para revelar o que já está na tela não é ação, é obstáculo.

## Resolvidas — o resto da conferência

06/09/2026. Fecha #5, #21, #24, #44, #48, #49, #52, #57 e a parte de período da #79, e
implementa **SCR-0038 · Reset de Senha**.

### Reset de senha (#5 / SCR-0038)

O login dizia "Fale com o administrador do escritório". Era honesto e era a ausência da
tela. Agora são duas: `/esqueci-senha` pede o link, `/redefinir-senha` gasta.

Quatro decisões que o teste segura:

**A resposta é 204 exista a conta ou não.** Dizer "esse e-mail não está cadastrado"
transformaria a página num verificador de quem trabalha no escritório, aberto a qualquer
um — e não haveria ganho, porque quem tem a conta recebe o e-mail de qualquer jeito. É a
mesma decisão do `_CREDENCIAIS_INVALIDAS` do login.

**Expirado e já usado dão a mesma resposta**, e pelo mesmo motivo: a diferença entre
"esse link já foi usado" e "esse link nunca existiu" é sinal para quem está testando
links.

**O token é gasto num UPDATE condicional**, como o refresh. Ler, decidir e depois gravar
é uma corrida — e aqui ela é pior que na renovação de sessão: dois cliques no mesmo link
deixariam duas senhas novas disputando qual fica, e a pessoa não saberia com qual entrou.

**Redefinir derruba todas as sessões.** Quem redefine ou esqueceu a senha ou desconfia
que alguém a tem; nos dois casos, deixar de pé a sessão aberta noutro lugar é deixar de pé
exatamente o que o reset veio fechar.

O e-mail sai pelo outbox, na mesma transação do token: link enviado sem token gravado é
link que não funciona, e token gravado sem link é ninguém avisado. Tabela própria, e não
coluna em `users`, porque o token tem vida própria — um pedido novo não pode apagar o
anterior sem que se saiba qual dos dois links chegou primeiro à caixa da pessoa.

### O logo (#49)

Sobe arquivo **ou** aponta URL. O campo continua sendo uma URL no banco; o que muda é que
agora existe uma para apontar sem o escritório ter onde hospedar a imagem — pedir só a URL
era não ter o recurso para quem só tem o arquivo. PNG e SVG, 2 MB, conferidos pelo tamanho
**lido** e não pelo `content-length`, que é declaração do cliente.

A gravação da chave não passa pela concorrência otimista de BR-MIGRAR-027, e é o único
lugar onde isso vale: o carimbo que o cliente leu não diz nada sobre um arquivo mandado
depois, e recusar por conflito deixaria o arquivo no disco com a configuração apontando
para o anterior.

### O tipo do Fale Conosco (#44)

`contact_messages.type` virou catálogo. O sintoma estava nas duas pontas: o formulário
público oferecia "Problema" e "Dúvida", que a triagem nunca soube exibir, e um seed
inventado gravou "suporte" e "comercial" sem o servidor reclamar. O filtro passa a listar
o catálogo inteiro em vez do que existe no banco — um filtro montado a partir das linhas
some quando a caixa esvazia e volta quando alguém escreve.

### Editar ciclo (#24) e reativar formulário (#48)

Editar ciclo vale **só para rascunho**. Depois de aberto há requests apontando para o
formulário e prazos que as pessoas já viram: trocar o formulário mudaria as perguntas
embaixo de quem responde, e mudar a data faria o atraso de BR-MIGRAR-007 mudar de resposta
para o passado. Corrigir ciclo em curso é estender, que é outra operação e tem outro nome.

Arquivar formulário ganhou volta. O legado chamava o par de "Ativar/Desativar", e sem o
outro lado um clique errado obrigava a recriar formulário e perguntas — com os ciclos
antigos apontando para um e os novos para outro de mesmo nome.

### O selo de papel (#57)

Mostra "Gestor (Admin)" enquanto a troca de contexto está em curso. Junto veio um defeito:
o seletor "Ver como…" lia o papel persistido, então voltava sozinho ao original depois de
trocar. `/auth/me` passou a devolver `active_role` — o papel que autoriza continua sendo o
persistido, e essa distinção é a própria BR-MIGRAR-016.

### #2 fica como desvio deliberado

O logo no login exigiria um endpoint público que diga de quem é a instalação. O legado
podia porque tinha um tenant só; aqui, estampar a marca antes do login é publicar o nome
do cliente para quem só abriu a URL. O nome do produto fica; a marca do escritório aparece
depois de entrar.

## Resolvidas — o banner do Início e a tela de feedback livre (#8)

06/09/2026, no fecho da conferência. A #8 estava marcada como "entra junto com a
SCR-0023", e a SCR-0023 existia pela metade: o formulário morava em `/minha-equipe`, e o
banner do Início apontava para lá.

Só que ali só chega quem tem equipe. A API nunca pediu vínculo entre quem escreve e quem
recebe — qualquer pessoa pode escrever para qualquer colega —, e prender a entrada na tela
do gestor transformava um recurso de todo mundo num recurso de alguns. O colaborador via o
banner, clicava, e caía numa tela que o menu nem lhe oferecia.

Agora o formulário é `components/feedback-livre.tsx`, usado pelas duas telas, e
`/feedback-livre` é a tela própria: busca por nome ou cargo e um botão por pessoa. Busca
com resultado, e não `select`, pelo mesmo motivo da #78 — com quarenta nomes o seletor vira
rolagem.

`GET /colleagues` devolve **só nome e cargo**, e é aberta a qualquer autenticado. Não é
`ProfileSummary`: ali vão e-mail, papel, capacidades e vínculo, que são assunto da
administração. O que esta lista diz é o que qualquer pessoa do escritório já sabe olhando
em volta. Quem pede sai da lista, porque a API recusa feedback para si mesmo e oferecer a
opção seria montar um caminho que termina em erro.

## Resolvidas — BUG-08

"Usuários removidos" renderizava **duas vezes** na Auditoria: uma dentro do bloco do
resumo e outra abaixo dele. Sobra de um lote anterior — a seção foi inserida no lugar novo
sem a antiga sair.

## Verificado rodando — 06/09/2026

O que os testes não pegam, conferido contra a stack local com o seed de demonstração:

| O quê | Resultado |
|---|---|
| Relatório de feedback livre | Diego 1 recebido, Marina 1 enviado, Rafael 1 recebido / 1 anônimo / 1 sensível — bate com o seed |
| Meu Histórico do Rafael | o feedback sensível **sobre ele** não aparece; ciclo e cliente aparecem |
| Histórico da equipe do gestor | só o feedback livre do Diego |
| Histórico da equipe do admin | os dois, inclusive o sensível anônimo |
| Marcar ciente | 204, e a marca volta como "Ciente em … por Rafael Antunes" |
| Reset: pedido para conta existente e inexistente | 204 nos dois |
| Reset: link no e-mail do worker | chegou, com `?token=…` |
| Reset: usar o link | 204; reusar o mesmo link → 401 |
| Reset: senha antiga depois da troca | 401; senha nova → 200 |
| Logo: upload PNG | 200, e `GET /settings/logo` devolve `image/png` |
| Logo: reenvio | 200 — é o caso que a concorrência otimista teria recusado |
| Logo: `text/plain` | 422, "O logo precisa ser PNG ou SVG" |
| Fale Conosco: tipo `duvida` | 422; `critica` → 201 |
| Editar ciclo aberto | 422, "Só rascunho pode ser editado" |
| Editar rascunho | 200 |
