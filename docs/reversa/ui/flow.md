# Fluxo de Navegação — A&S Feedback Hub

> Gerado pelo Visor (Reversa) em 2026-08-28. Baseado nos menus laterais e ações observadas nos screenshots; setas 🟡 são inferidas do código/rotas quando a transição não foi capturada.
> Legenda: retângulos = páginas; subrotinas ⟦⟧ = modais; tracejado = fluxo não capturado (inferido).

## Visão geral (papéis capturados: Admin e Coordenador)

```mermaid
flowchart TD
    login["/login<br/>Login"] -->|autenticação| routing{Papel do usuário}
    login -.->|"Esqueci minha senha"| reset["/reset-password 🟡"]
    routing -->|admin| admin["/admin<br/>Painel Administrativo"]
    routing -->|coordenador| coord["/coordenador<br/>Início"]
    routing -->|gestor| gestor["/gestor<br/>Início"]
    routing -->|colaborador| colab["/dashboard<br/>Início"]

    subgraph shared["Rotas compartilhadas (menu de todos os papéis avaliadores)"]
        anotacoes["/minhas-anotacoes<br/>Minhas Anotações"]
        meusfb["/meus-feedbacks<br/>Meus Feedbacks"]
        historico["/historico<br/>Meu Histórico"]
        perfil["/perfil<br/>Meu Perfil"]
        caderno[["⟦Caderno do Ciclo — botão flutuante 📖⟧"]]
        fbLivre[["⟦Dar Feedback Livre — banner⟧"]]
    end

    admin --- shared
    coord --- shared
    gestor --- shared
    colab --- shared
```

## Área do gestor (menu lateral)

```mermaid
flowchart LR
    gestor["/gestor<br/>Início"]
    gestorEquipe["/gestor/equipe<br/>Minha Equipe"]
    gestorPend["/gestor/pendentes<br/>Feedbacks Pendentes"]
    gestorHist["/gestor/historico<br/>Histórico da Equipe"]
    avalClientes["/avaliacoes-clientes<br/>Avaliações de Clientes"]

    gestor -->|"card Membros da Equipe"| gestorEquipe
    gestor --- gestorPend
    gestor --- gestorHist
    gestor --- avalClientes
    gestor --- compromissos["Compromissos"]
    gestorEquipe -.->|"💬 dar feedback"| fbForm2["FeedbackForm 🔴"]
    gestorEquipe -.->|"🔔 lembrete"| gestorPend
```

## Fluxo de avaliação do cliente externo (capturado de ponta a ponta)

```mermaid
flowchart TD
    avalClientes["/avaliacoes-clientes<br/>(gestor/colaborador)"] --> mSolicitar[["⟦Solicitar Avaliação de Cliente⟧<br/>nome*, WhatsApp*, e-mail, formulário"]]
    mSolicitar -->|"Gerar Link (expira em 7 dias)"| linkToken["Link /avaliacao?token=…"]
    linkToken -->|"WhatsApp / e-mail"| boasVindas["Boas-vindas<br/>'Leva menos de 2 minutos'"]
    boasVindas --> ident["Identificação<br/>(pré-preenchida)"]
    ident --> motiv{"Motivação?"}
    motiv -->|"Quero elogiar"| elogio["Textarea de elogio<br/>(encaminhado ao profissional)"]
    motiv -->|"Tive um problema"| problema["Textarea de relato<br/>(tratado com prioridade)"]
    motiv -->|"Avaliar / Outro"| transicao["Transição"]
    elogio --> transicao
    problema --> transicao
    transicao --> quiz["Perguntas 1–9<br/>(estrelas 0–10 + textos opcionais)"]
    quiz --> tipoServ["Tipo de serviço<br/>(multi-select: Trabalhista, Cível, …)"]
    tipoServ -->|"Enviar avaliação"| obrigado["Agradecimento ✅"]
    obrigado -.-> relatorios["Resultados em /admin/relatorios<br/>aba Clientes 🟡"]
```

## Área administrativa (menu lateral do admin)

```mermaid
flowchart LR
    admin["/admin<br/>Dashboard"]

    subgraph anot["Anotações"]
        minhasA["/minhas-anotacoes"]
        realizadas["/admin/anotacoes-realizadas<br/>Anotações Realizadas"]
    end

    subgraph rel["Relatórios (unit reports)"]
        dados["/admin/relatorios<br/>Dados e Filtros"]
        emitir["/admin/relatorio-feedback<br/>Emitir Relatório"]
    end

    subgraph gestao["Gestão"]
        equipe["/admin/equipe<br/>Minha Equipe"] --> mAddMembro[["⟦Adicionar Membro⟧"]]
        histEquipe["/admin/historico-equipe<br/>Histórico da Equipe"]
        usuarios["/admin/usuarios<br/>Usuários"] --> mNovoUser[["⟦Novo Usuário⟧"]]
        deptos["/admin/departamentos<br/>Departamentos"] --> mNovoDepto[["⟦Novo Departamento⟧"]]
    end

    subgraph ciclo360["Motor do 360° (domínio feedback)"]
        ciclos["/admin/ciclos<br/>Ciclos"] --> mNovoCiclo[["⟦Novo Ciclo — wizard 3 passos⟧"]]
        ciclos --> mEditCiclo[["⟦Editar Ciclo⟧"]]
        permissoes["/admin/permissoes<br/>Permissões"] --> mNovaPerm[["⟦Nova Permissão⟧"]]
        diagnostico["/admin/diagnostico<br/>Diagnóstico"]
        formularios["/admin/formularios<br/>Formulários (unit feedback)"] --> mNovoForm[["⟦Novo Formulário⟧"]]
        formularios -.->|"botão Perguntas 🔴"| editorPerguntas["Editor de perguntas"]
    end

    subgraph operacao["Operação"]
        auditoria["/admin/auditoria<br/>Auditoria"]
        faleconosco["/admin/faleconosco<br/>Fale Conosco"]
        agenda["/admin/agenda<br/>Agenda"] -.->|"Conectar Google Agenda (OAuth) 🟡"| gcallback["/google-callback"]
        atualizacoes["/admin/atualizacoes<br/>Atualizações"] -.->|"Publicar e notificar 🟡"| novidades["/novidades (leitura)"]
        config["/admin/configuracoes<br/>Configurações (unit company-settings)"]
    end

    admin -->|"Atenção Necessária → Usuários inativos"| usuarios
    admin -->|"Atenção Necessária → Ciclos sem formulário"| ciclos
    diagnostico -->|"ajustar permissões"| permissoes
```

## Área do coordenador (menu lateral)

```mermaid
flowchart LR
    coord["/coordenador<br/>Início"]
    coordEquipe["/coordenador/equipe<br/>Minha Equipe"]
    coordPend["/coordenador/pendentes<br/>Feedbacks Pendentes"]
    coordHist["/coordenador/historico<br/>Histórico da Equipe"]
    meusfb["/meus-feedbacks"]
    historico["/historico"]

    coord -->|"card Membros da Equipe"| coordEquipe
    coord -.->|"+ Anotar"| anotacoes["/minhas-anotacoes"]
    coordEquipe -.->|"ícone 💬 dar feedback 🟡"| fbForm["FeedbackForm 🔴"]
    coordEquipe -.->|"ícone 🔔 lembrete 🟡"| coordPend
    coord --- coordPend
    coord --- coordHist
    coord --- meusfb
    coord --- historico
```

## Fluxos principais identificados

1. **Ciclo 360° (admin):** Formulários → Ciclos (criar com formulário associado) → Permissões (quem avalia quem) → Diagnóstico (validar antes do fechamento) → fechamento automático 08:00 (auditoria) → Publicar resultados → aparecem em Meu Histórico dos avaliados 🟡
2. **Avaliação pelo avaliador:** Meus Feedbacks (requests pendentes) → FeedbackForm (responder) 🟡 → enviado/abdicado → Auditoria registra "Feedback 360° Enviado" 🟢
3. **Feedback livre:** banner "Dar Feedback para alguém" (qualquer tela inicial) → envio → destinatário dá ciência (badge "Ciente em …") → visível em Histórico da Equipe 🟢
4. **Supervisão (coordenador/admin):** Início (KPIs) → Feedbacks Pendentes → lembrete 🔔 → Histórico da Equipe 🟢
5. **Avaliação de cliente externo:** Avaliações de Clientes (solicitar → gerar link tokenizado, expira em 7 dias, enviado por WhatsApp com template de Configurações) → wizard público `/avaliacao?token=…` (motivação com ramos, 9 perguntas, tipo de serviço) → resultados em Relatórios aba Clientes 🟢 (fluxo capturado de ponta a ponta)
6. **Denúncia protegida:** modal Dar Feedback Livre → checkbox de situação grave (assédio, discriminação…) → feedback oculto do destinatário, visível só a gestores/admins 🟢
7. **Anotação contínua:** Caderno do Ciclo (botão 📖 flutuante, texto ou áudio) → Minhas Anotações → subsidia o preenchimento dos feedbacks do ciclo 🟢

## Pontos de entrada e saída

- **Entrada:** `/login` (único ponto autenticado observado); `ClientFeedbackPage` pública via link enviado ao cliente 🟡
- **Saída:** item "Sair" no rodapé do menu lateral (todas as telas) 🟢
