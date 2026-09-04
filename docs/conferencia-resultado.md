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
| Conferidas | 4 de 35 — SCR-0035, SCR-0001, SCR-0003, SCR-0007 |
| Defeitos próprios encontrados | 2 (um deles bloqueava a conferência; ambos corrigidos) |
| Divergências contra o oráculo | 18 registradas abaixo |

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

---

## O que fazer com isto

Nada aqui foi decidido: divergência encontrada não é divergência aprovada. Cada linha
acima termina em uma de três saídas, e quem decide é o cliente na homologação:

1. **Implementar** — o legado tinha e faz falta (as seções do painel, as colunas e
   filtros de Usuários, o revelar-senha do login).
2. **Aprovar como deviation** — o novo é deliberadamente diferente; vai para
   `screen_deviation_log.md` com o motivo.
3. **Descartar** — o legado tinha e ninguém usava.

As que já têm dono claro: a #5 do login entra junto com a SCR-0038, e a #8 do painel
junto com a SCR-0023.
