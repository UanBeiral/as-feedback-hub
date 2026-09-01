# Telas — unit `public`

> Gerado pelo Visor (Reversa) em 2026-08-28 a partir de screenshots do sistema em produção (`aesfeedbackinterno.vercel.app`).
> Escala de confiança: 🟢 CONFIRMADO (visível no screenshot) · 🟡 INFERIDO · 🔴 LACUNA

---

## Avaliação Pública do Cliente (wizard)

- **Rota:** `/avaliacao?token=<token>` · **Arquivo:** `src/pages/public/ClientFeedbackPage.tsx`
- **Screenshots:** 16 capturas `screenshots/avaliacao-*.png` (fluxo completo, do boas-vindas ao agradecimento)
- **Acesso:** link tokenizado gerado em "Avaliações de Clientes" (expira em 7 dias), enviado por WhatsApp/e-mail 🟢
- **Layout:** página limpa sem shell autenticado — card central sobre fundo claro, barra de progresso roxa no topo do card, botões Voltar/Continuar em gradiente roxo 🟢. Identidade visual distinta do app interno (mesma família do login) 🟢

### Etapas observadas (na ordem)

| # | Etapa | Screenshot | Conteúdo |
|---|-------|-----------|----------|
| 0 | Boas-vindas | `avaliacao-boas-vindas.png` | Logo A&S + "Sua opinião transforma nosso atendimento" + badge "⏱ Leva menos de 2 minutos" + **Começar avaliação** 🟢 |
| 1 | Identificação | `avaliacao-identificacao.png` | "Como podemos te chamar?" — Seu nome * e WhatsApp * **pré-preenchidos** com os dados da solicitação; E-mail (opcional — "Informe para receber confirmação da sua avaliação") 🟢 |
| 2 | Motivação | `avaliacao-motivacao.png` | "O que motivou sua avaliação?" — 4 cards: ❤️ Quero elogiar · ⭐ Quero avaliar o atendimento · ⚠️ Tive um problema · 💬 Outro motivo 🟢 |
| 2a | Ramo problema | `avaliacao-relato-problema.png` | "Lamentamos. Conte-nos o que aconteceu" — "Seu relato será tratado com prioridade pela nossa equipe." — textarea obrigatória (Continuar desabilitado vazio) 🟢 |
| 2b | Ramo elogio | `avaliacao-elogio.png` | "Que bom! Conte-nos o que fizemos de especial" — "Seu elogio será encaminhado diretamente ao profissional." — textarea 🟢 |
| 3 | Transição | `avaliacao-transicao.png` | "Vamos avaliar o atendimento — Agora vamos conhecer sua experiência em detalhes." 🟢 |
| 4 | Q1 de 9 | `avaliacao-q1-experiencia-geral.png` | "No geral, como você avalia a experiência com <profissional>?" — **10 estrelas (escala 0–10)**, valor mostrado "10/10" em verde 🟢 |
| 5 | Q2 de 9 | `avaliacao-q2-atendimento.png` | "Como você avalia o atendimento recebido pelo profissional?" — estrelas 🟢 |
| 6 | Q3 de 9 | `avaliacao-q3-clareza.png` | "O profissional foi claro e objetivo nas explicações?" — estrelas 🟢 |
| 7 | Q4 de 9 | `avaliacao-q4-agilidade.png` | "Como avalia a agilidade no retorno às suas demandas?" — estrelas 🟢 |
| 8 | Q5 de 9 | `avaliacao-q5-acolhimento.png` | "Você se sentiu ouvido(a) e bem acolhido(a)?" — estrelas 🟢 |
| 9 | Q6 de 9 | — | 🔴 não capturada (entre Q5 e Q7; provável nota de recomendação/NPS, coluna "Recomendação" existe nos relatórios) |
| 10 | Q7 de 9 | `avaliacao-q7-pontos-fortes.png` | "O que o profissional fez de melhor?" — textarea "Opcional — mas toda opinião é valiosa" 🟢 |
| 11 | Q8 de 9 | `avaliacao-q8-melhorias.png` (+ `-2`) | "O que poderia ser melhorado?" — textarea opcional 🟢 |
| 12 | Q9 de 9 | `avaliacao-q9-satisfacao.png` | "No geral, quão satisfeito(a) você ficou com o atendimento de <profissional>?" — estrelas; botão final **"Quase lá!"** (desabilitado sem nota) 🟢 |
| 13 | Tipo de serviço | `avaliacao-tipo-servico.png` | "Que tipo de serviço foi prestado? — Pode selecionar mais de um" — chips multi-select: Trabalhista, Cível, Criminal, Tributário, Empresarial, Contratos, Consultoria, Família, Imobiliário, Previdenciário, **+ Outro…**; botão verde **Enviar avaliação** 🟢 |
| 14 | Agradecimento | `avaliacao-agradecimento.png` | "✅ Obrigado, <nome>! Sua avaliação é muito importante para nós…" 🟢 |

### Regras observadas

- O questionário de 9 perguntas corresponde ao formulário configurável (dropdown "Formulário: Atendimento Jurídico Geral" na solicitação) — perguntas por template 🟡
- A motivação escolhida na etapa 2 alimenta a coluna "Motivação" dos relatórios (Avaliação/Problema/Outro) e o ramo condicional de texto 🟢
- Notas em estrelas mapeiam para escala 0–10 exibida nos relatórios ("Nota Geral 9/10") 🟢
- 🔴 LACUNA: comportamento com token expirado/já respondido não capturado; Q6 ausente.
