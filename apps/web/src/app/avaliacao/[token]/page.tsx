"use client";

/**
 * Wizard público de avaliação de cliente (SCR-0035 / PAR-03).
 *
 * A única tela do sistema sem sessão, e a única que um estranho carrega. Quatro
 * cuidados que ela carrega:
 *
 * - **Não fala com nada além do endpoint público.** Nenhuma chamada autenticada,
 *   nenhum dado do escritório além do necessário para desenhar as etapas.
 * - **Link inválido, expirado ou já respondido mostram a mesma mensagem.** Distinguir
 *   contaria a um estranho que aquele link um dia valeu — e ele circula por WhatsApp.
 * - **Enviar duas vezes mostra a mesma confirmação.** O servidor trata o duplo clique
 *   como sucesso; a tela não inventa um erro que ele não deu.
 * - **Nada é enviado antes da última etapa.** Não há rascunho parcial: quem desistir no
 *   meio não deixa avaliação pela metade no relatório de ninguém.
 *
 * Sobre o número de etapas: o oráculo tem 16 telas porque o formulário do escritório
 * tinha 9 perguntas (boas-vindas, identificação, motivação, ramo condicional,
 * transição, 9 perguntas, tipo de serviço, agradecimento). Aqui a contagem é
 * **derivada** — o formulário é configurável, o ramo depende da motivação escolhida e o
 * tenant pode desligar motivações. Com o formulário de 9 perguntas do oráculo o wizard
 * dá exatamente as mesmas 16 telas; com outro formulário, dá o que aquele formulário
 * pedir. Fixar 16 no código seria copiar o acidente, não a regra.
 */

import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import {
  AreaDeTextoPublica,
  BotaoDoWizard,
  CampoPublico,
  CartaoDeEscolha,
  ChipDeServico,
  ContadorDePerguntas,
  EntradaPublica,
  Estrelas,
  IconeAlerta,
  IconeBalao,
  IconeCheck,
  IconeCoracao,
  IconeEstrela,
  IconeRelogio,
  MolduraDoWizard,
  RodapeDaEtapa,
  SubtituloDaEtapa,
  TituloDaEtapa,
} from "@/components/publico";
import { ApiError, api } from "@/lib/api";
import type { FormularioPublico, PerguntaPublica } from "@/lib/tipos";

/** Nota máxima das estrelas. O oráculo mostra 10 e os relatórios exibem "9/10". */
const NOTA_MAXIMA = 10;

type Motivacao = "praise" | "evaluate" | "problem" | "other";

const MOTIVACOES: Record<Motivacao, { rotulo: string; icone: React.ReactNode }> = {
  praise: { rotulo: "Quero elogiar", icone: <IconeCoracao className="h-6 w-6" /> },
  evaluate: { rotulo: "Quero avaliar o atendimento", icone: <IconeEstrela className="h-6 w-6" /> },
  problem: { rotulo: "Tive um problema", icone: <IconeAlerta className="h-6 w-6" /> },
  other: { rotulo: "Outro motivo", icone: <IconeBalao className="h-6 w-6" /> },
};

/** Só elogio e problema abrem o ramo de texto; avaliar e outro seguem direto. */
const MOTIVACOES_COM_RAMO: Motivacao[] = ["praise", "problem"];

/**
 * O contrato diz `string[]`, porque o catálogo de settings é texto livre. Filtrar aqui
 * é o que garante que uma chave nova no backend apareça como etapa faltando, e não como
 * card em branco na tela do cliente.
 */
function ehMotivacao(chave: string): chave is Motivacao {
  return chave in MOTIVACOES;
}

const RAMO: Record<"praise" | "problem", { titulo: string; apoio: string; exemplo: string }> = {
  praise: {
    titulo: "Que bom! Conte-nos o que fizemos de especial",
    apoio: "Seu elogio será encaminhado diretamente ao profissional.",
    exemplo: "Conte o que fez a diferença para você…",
  },
  problem: {
    titulo: "Lamentamos. Conte-nos o que aconteceu",
    apoio: "Seu relato será tratado com prioridade pela nossa equipe.",
    exemplo: "Descreva o que aconteceu para que possamos resolver…",
  },
};

type Etapa =
  | { tipo: "boas-vindas" }
  | { tipo: "identificacao" }
  | { tipo: "motivacao"; opcoes: Motivacao[] }
  | { tipo: "ramo"; motivacao: "praise" | "problem" }
  | { tipo: "transicao" }
  | { tipo: "pergunta"; pergunta: PerguntaPublica; posicao: number; total: number }
  | { tipo: "servicos" };

type Resposta = { texto: string; nota: number | null };

/**
 * Progresso da barra do topo, medido no oráculo (screenshots de `public/`).
 *
 * A escala tem seis casas e **não** é "etapa atual ÷ total": identificação marca 1/6,
 * o bloco inteiro de motivação/ramo/transição marca 2/6, as perguntas interpolam de
 * 3/6 a 4/6 conforme a posição, e o tipo de serviço marca 5/6. Boas-vindas e
 * agradecimento não mostram barra nenhuma. Reproduzido assim de propósito: é o que a
 * conferência contra o oráculo compara.
 */
function progressoDe(etapa: Etapa): number | null {
  switch (etapa.tipo) {
    case "boas-vindas":
      return null;
    case "identificacao":
      return (1 / 6) * 100;
    case "motivacao":
    case "ramo":
    case "transicao":
      return (2 / 6) * 100;
    case "pergunta":
      return ((3 + etapa.posicao / etapa.total) / 6) * 100;
    case "servicos":
      return (5 / 6) * 100;
  }
}

function ehEscala(pergunta: PerguntaPublica): boolean {
  return pergunta.question_type === "rating" || pergunta.question_type === "nps";
}

export default function AvaliacaoPublica() {
  const parametros = useParams<{ token: string }>();
  const [formulario, setFormulario] = useState<FormularioPublico | null>(null);
  const [indisponivel, setIndisponivel] = useState(false);

  const [passo, setPasso] = useState(0);
  const [contato, setContato] = useState({ nome: "", whatsapp: "", email: "" });
  const [motivacao, setMotivacao] = useState<Motivacao | null>(null);
  const [relato, setRelato] = useState("");
  const [respostas, setRespostas] = useState<Record<string, Resposta>>({});
  const [tags, setTags] = useState<string[]>([]);

  const [enviado, setEnviado] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    api<FormularioPublico>(`/public/evaluations/${parametros.token}`, { publico: true })
      .then((aberto) => {
        setFormulario(aberto);
        // A identificação nasce com o que o escritório digitou na solicitação.
        setContato({
          nome: aberto.client_name ?? "",
          whatsapp: aberto.client_whatsapp ?? "",
          email: aberto.client_email ?? "",
        });
      })
      .catch(() => setIndisponivel(true));
  }, [parametros.token]);

  /**
   * As etapas são derivadas do formulário e da motivação escolhida.
   *
   * O ramo entra e sai da lista conforme a escolha da etapa anterior, e é por isso que
   * ele fica logo **depois** de `motivacao`: voltar, trocar a motivação e seguir mantém
   * o índice do passo válido, sem precisar remendar o contador.
   */
  const etapas = useMemo<Etapa[]>(() => {
    if (formulario === null) return [];
    const perguntas = formulario.questions;
    const opcoes = formulario.motivations.filter(ehMotivacao);

    const lista: Etapa[] = [{ tipo: "boas-vindas" }, { tipo: "identificacao" }];

    if (opcoes.length > 0) {
      lista.push({ tipo: "motivacao", opcoes });
      if (motivacao === "praise" || motivacao === "problem") {
        lista.push({ tipo: "ramo", motivacao });
      }
    }

    if (perguntas.length > 0) {
      lista.push({ tipo: "transicao" });
      perguntas.forEach((pergunta, indice) =>
        lista.push({
          tipo: "pergunta",
          pergunta,
          posicao: indice + 1,
          total: perguntas.length,
        }),
      );
    }

    if (formulario.service_tags.length > 0) lista.push({ tipo: "servicos" });
    return lista;
  }, [formulario, motivacao]);

  const etapa = etapas[Math.min(passo, etapas.length - 1)];
  const ultima = passo >= etapas.length - 1;

  function avancar() {
    setErro(null);
    setPasso((atual) => Math.min(atual + 1, etapas.length - 1));
  }

  function voltar() {
    setErro(null);
    setPasso((atual) => Math.max(atual - 1, 0));
  }

  function responder(id: string, mudanca: Partial<Resposta>) {
    setRespostas((atual) => {
      const anterior: Resposta = atual[id] ?? { texto: "", nota: null };
      return { ...atual, [id]: { ...anterior, ...mudanca } };
    });
  }

  async function enviar() {
    if (formulario === null) return;
    setErro(null);
    setEnviando(true);

    const respondidas = formulario.questions
      .map((pergunta) => ({ pergunta, resposta: respostas[pergunta.id] }))
      .filter(({ resposta }) => resposta && (resposta.nota !== null || resposta.texto.trim()));

    // A primeira pergunta de escala vira a nota geral e a de NPS vira a recomendação:
    // são as duas colunas que os relatórios exibem, e o wizard não tem etapa própria
    // para elas. Ver DEV-A12 em docs/spec-deviations.md.
    const escalas = respondidas.filter(({ pergunta }) => ehEscala(pergunta));
    const notaGeral = escalas.find(({ pergunta }) => pergunta.question_type === "rating");
    const recomendacao = escalas.find(({ pergunta }) => pergunta.question_type === "nps");

    try {
      await api(`/public/evaluations/${parametros.token}`, {
        publico: true,
        method: "POST",
        body: {
          answers: respondidas.map(({ pergunta, resposta }) => ({
            question_id: pergunta.id,
            text_value: resposta.texto.trim() || null,
            rating_value: resposta.nota,
          })),
          client_name: contato.nome.trim() || null,
          client_whatsapp: contato.whatsapp.trim() || null,
          client_email: contato.email.trim() || null,
          contact_motivation: motivacao,
          contact_motivation_text: relato.trim() || null,
          overall_rating: notaGeral?.resposta.nota ?? null,
          recommendation_rating: recomendacao?.resposta.nota ?? null,
          service_tag_ids: tags,
        },
      });
      setEnviado(true);
    } catch (falha) {
      setErro(
        falha instanceof ApiError && falha.status === 422
          ? "Faltou responder alguma pergunta obrigatória. Volte e confira, por favor."
          : "Não foi possível enviar sua avaliação agora. Tente de novo em instantes.",
      );
    } finally {
      setEnviando(false);
    }
  }

  /* ---------------------------------------------------------------- desfechos */

  if (indisponivel) {
    return (
      <MolduraDoWizard progresso={null}>
        <TituloDaEtapa>Link indisponível</TituloDaEtapa>
        <SubtituloDaEtapa>
          Este link de avaliação não é válido ou já foi utilizado. Se você recebeu o
          convite há pouco tempo, peça um novo ao escritório.
        </SubtituloDaEtapa>
      </MolduraDoWizard>
    );
  }

  if (enviado) {
    const primeiroNome = contato.nome.trim().split(/\s+/)[0];
    return (
      <MolduraDoWizard progresso={null}>
        <div className="flex flex-col items-center text-center">
          <span className="flex h-16 w-16 items-center justify-center rounded-full bg-success text-success-foreground">
            <IconeCheck className="h-8 w-8" />
          </span>
          <h1 className="mt-6 text-xl font-semibold text-card-foreground">
            {primeiroNome ? `Obrigado, ${primeiroNome}!` : "Obrigado!"}
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Sua avaliação é muito importante para nós. Você é uma das pessoas que nos
            ajudam a melhorar cada dia.
          </p>
        </div>
      </MolduraDoWizard>
    );
  }

  if (formulario === null || etapa === undefined) {
    return (
      <MolduraDoWizard progresso={null}>
        <p className="py-8 text-center text-sm text-muted-foreground">Carregando…</p>
      </MolduraDoWizard>
    );
  }

  /* ---------------------------------------------------------------- etapas */

  const avaliado = formulario.target_name;
  const aoVoltar = passo === 0 ? undefined : voltar;

  return (
    <MolduraDoWizard progresso={progressoDe(etapa)}>
      {etapa.tipo === "boas-vindas" && (
        <BoasVindas empresa={formulario.company_name} aoComecar={avancar} />
      )}

      {etapa.tipo === "identificacao" && (
        <>
          <TituloDaEtapa>Como podemos te chamar?</TituloDaEtapa>
          <div className="mt-6 space-y-4">
            <CampoPublico rotulo="Seu nome" obrigatorio>
              <EntradaPublica
                autoFocus
                value={contato.nome}
                onChange={(e) => setContato({ ...contato, nome: e.target.value })}
              />
            </CampoPublico>
            <CampoPublico rotulo="WhatsApp" obrigatorio>
              <EntradaPublica
                inputMode="tel"
                value={contato.whatsapp}
                onChange={(e) => setContato({ ...contato, whatsapp: e.target.value })}
              />
            </CampoPublico>
            <CampoPublico
              rotulo="E-mail"
              opcional
              dica="Informe para receber confirmação da sua avaliação"
            >
              <EntradaPublica
                type="email"
                placeholder="seu@email.com"
                value={contato.email}
                onChange={(e) => setContato({ ...contato, email: e.target.value })}
              />
            </CampoPublico>
          </div>
          <RodapeDaEtapa aoVoltar={aoVoltar}>
            <BotaoDoWizard
              onClick={avancar}
              desabilitado={!contato.nome.trim() || !contato.whatsapp.trim()}
            >
              Continuar
            </BotaoDoWizard>
          </RodapeDaEtapa>
        </>
      )}

      {etapa.tipo === "motivacao" && (
        <>
          <TituloDaEtapa>O que motivou sua avaliação?</TituloDaEtapa>
          <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2">
            {etapa.opcoes.map((chave) => (
              <CartaoDeEscolha
                key={chave}
                icone={MOTIVACOES[chave].icone}
                rotulo={MOTIVACOES[chave].rotulo}
                onClick={() => {
                  setMotivacao(chave);
                  // Trocar de motivação depois de escrever deixaria o relato órfão,
                  // preso a um ramo que não é mais o escolhido.
                  if (!MOTIVACOES_COM_RAMO.includes(chave)) setRelato("");
                  avancar();
                }}
              />
            ))}
          </div>
          <RodapeDaEtapa aoVoltar={aoVoltar} />
        </>
      )}

      {etapa.tipo === "ramo" && (
        <>
          <TituloDaEtapa>{RAMO[etapa.motivacao].titulo}</TituloDaEtapa>
          <SubtituloDaEtapa>{RAMO[etapa.motivacao].apoio}</SubtituloDaEtapa>
          <div className="mt-5">
            <AreaDeTextoPublica
              autoFocus
              aria-label={RAMO[etapa.motivacao].titulo}
              placeholder={RAMO[etapa.motivacao].exemplo}
              value={relato}
              onChange={(e) => setRelato(e.target.value)}
            />
          </div>
          <RodapeDaEtapa aoVoltar={aoVoltar}>
            <BotaoDoWizard onClick={avancar} desabilitado={!relato.trim()}>
              Continuar
            </BotaoDoWizard>
          </RodapeDaEtapa>
        </>
      )}

      {etapa.tipo === "transicao" && (
        <>
          <TituloDaEtapa>Vamos avaliar o atendimento</TituloDaEtapa>
          <SubtituloDaEtapa>Agora vamos conhecer sua experiência em detalhes.</SubtituloDaEtapa>
          <RodapeDaEtapa aoVoltar={aoVoltar}>
            <BotaoDoWizard onClick={avancar}>Continuar</BotaoDoWizard>
          </RodapeDaEtapa>
        </>
      )}

      {etapa.tipo === "pergunta" && (
        <EtapaDePergunta
          etapa={etapa}
          avaliado={avaliado}
          resposta={respostas[etapa.pergunta.id]}
          aoResponder={(mudanca) => responder(etapa.pergunta.id, mudanca)}
          aoVoltar={aoVoltar}
          ultima={ultima}
          enviando={enviando}
          aoAvancar={ultima ? enviar : avancar}
          // "Quase lá!" é o rótulo do oráculo na última pergunta quando ainda falta a
          // etapa de tipo de serviço; quando ela não existe, esta é a etapa de envio.
          rotulo={
            ultima ? "Enviar avaliação" : etapa.posicao === etapa.total ? "Quase lá!" : "Continuar"
          }
        />
      )}

      {etapa.tipo === "servicos" && (
        <>
          <TituloDaEtapa>Que tipo de serviço foi prestado?</TituloDaEtapa>
          <SubtituloDaEtapa>Pode selecionar mais de um</SubtituloDaEtapa>
          <div className="mt-5 flex flex-wrap gap-2">
            {formulario.service_tags.map((tag) => (
              <ChipDeServico
                key={tag.id}
                marcada={tags.includes(tag.id)}
                onClick={() =>
                  setTags((atual) =>
                    atual.includes(tag.id)
                      ? atual.filter((id) => id !== tag.id)
                      : [...atual, tag.id],
                  )
                }
              >
                {tag.name}
              </ChipDeServico>
            ))}
          </div>
          <RodapeDaEtapa aoVoltar={aoVoltar}>
            <BotaoDoWizard variante="conclusao" onClick={enviar} desabilitado={enviando}>
              {enviando ? "Enviando…" : "Enviar avaliação"}
            </BotaoDoWizard>
          </RodapeDaEtapa>
        </>
      )}

      {erro && (
        <p className="mt-4 text-sm text-destructive" role="alert">
          {erro}
        </p>
      )}
    </MolduraDoWizard>
  );
}

/* ------------------------------------------------------------------ capa */

function BoasVindas({ empresa, aoComecar }: { empresa: string | null; aoComecar: () => void }) {
  return (
    <div className="flex flex-col items-center text-center">
      <span className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary text-lg font-semibold text-primary-foreground">
        {iniciais(empresa)}
      </span>
      <h1 className="mt-6 text-2xl font-semibold leading-snug text-card-foreground">
        Sua opinião transforma
        <br />
        nosso atendimento
      </h1>
      <p className="mt-3 text-sm text-muted-foreground">
        Sua avaliação nos ajuda a oferecer um atendimento cada vez melhor.
      </p>
      <span className="mt-6 inline-flex items-center gap-1.5 rounded-full bg-publico-de/10 px-4 py-2 text-xs text-publico-de">
        <IconeRelogio className="h-4 w-4" />
        Leva menos de 2 minutos
      </span>
      <div className="mt-6 w-full">
        <BotaoDoWizard onClick={aoComecar} larguraTotal>
          Começar avaliação
        </BotaoDoWizard>
      </div>
    </div>
  );
}

/**
 * Monograma do escritório. O legado estampava a marca A&S; aqui a marca vem do tenant,
 * porque o nome do escritório é configuração e não constante do código.
 */
function iniciais(empresa: string | null): string {
  const palavras = (empresa ?? "").trim().split(/\s+/).filter(Boolean);
  if (palavras.length === 0) return "★";
  return palavras
    .slice(0, 2)
    .map((palavra) => palavra[0]?.toUpperCase() ?? "")
    .join("");
}

/* ------------------------------------------------------------------ pergunta */

function EtapaDePergunta({
  etapa,
  avaliado,
  resposta,
  aoResponder,
  aoVoltar,
  aoAvancar,
  rotulo,
  ultima,
  enviando,
}: {
  etapa: Extract<Etapa, { tipo: "pergunta" }>;
  avaliado: string | null;
  resposta: Resposta | undefined;
  aoResponder: (mudanca: Partial<Resposta>) => void;
  aoVoltar?: () => void;
  aoAvancar: () => void;
  rotulo: string;
  ultima: boolean;
  enviando: boolean;
}) {
  const { pergunta, posicao, total } = etapa;
  const nota = resposta?.nota ?? null;
  const texto = resposta?.texto ?? "";
  const escala = ehEscala(pergunta);

  const respondida = escala ? nota !== null : texto.trim().length > 0;
  const bloqueia = pergunta.is_required && !respondida;

  return (
    <>
      <ContadorDePerguntas atual={posicao} total={total} />
      <TituloDaEtapa centralizado>{comAvaliado(pergunta.question_text, avaliado)}</TituloDaEtapa>

      {escala ? (
        <Estrelas
          valor={nota}
          maximo={NOTA_MAXIMA}
          rotulo={pergunta.question_text}
          aoEscolher={(escolha) => aoResponder({ nota: escolha })}
        />
      ) : pergunta.question_type === "yes_no" ? (
        <div className="mt-6 grid grid-cols-2 gap-3">
          {[
            { valor: "sim", rotulo: "Sim" },
            { valor: "nao", rotulo: "Não" },
          ].map((opcao) => (
            <button
              key={opcao.valor}
              type="button"
              aria-pressed={texto === opcao.valor}
              onClick={() => aoResponder({ texto: texto === opcao.valor ? "" : opcao.valor })}
              className={
                "rounded-xl border px-4 py-4 text-sm transition focus-visible:outline-none " +
                "focus-visible:ring-2 focus-visible:ring-publico-de " +
                (texto === opcao.valor
                  ? "border-publico-de bg-publico-de/10 font-medium text-publico-de"
                  : "border-border text-card-foreground hover:bg-muted")
              }
            >
              {opcao.rotulo}
            </button>
          ))}
        </div>
      ) : (
        <div className="mt-5">
          <AreaDeTextoPublica
            aria-label={pergunta.question_text}
            placeholder={pergunta.placeholder ?? ""}
            value={texto}
            onChange={(e) => aoResponder({ texto: e.target.value })}
          />
          {!pergunta.is_required && (
            <p className="mt-3 text-center text-sm text-muted-foreground">
              Opcional — mas toda opinião é valiosa
            </p>
          )}
        </div>
      )}

      <RodapeDaEtapa aoVoltar={aoVoltar}>
        <BotaoDoWizard
          variante={ultima ? "conclusao" : "gradiente"}
          onClick={aoAvancar}
          desabilitado={bloqueia || (ultima && enviando)}
        >
          {ultima && enviando ? "Enviando…" : rotulo}
        </BotaoDoWizard>
      </RodapeDaEtapa>
    </>
  );
}

/**
 * Destaca o nome de quem está sendo avaliado dentro do texto da pergunta.
 *
 * O escritório escreve "…com {profissional}?" no editor de perguntas; a substituição
 * acontece aqui e o nome sai em cor de destaque, como no oráculo. Pergunta sem o
 * marcador segue inteira, sem invenção.
 */
function comAvaliado(texto: string, avaliado: string | null): React.ReactNode {
  const partes = texto.split(/\{profissional\}/g);
  if (partes.length === 1 || !avaliado) return partes.join(avaliado ?? "");
  return partes.map((parte, indice) => (
    <span key={indice}>
      {parte}
      {indice < partes.length - 1 && <span className="text-publico-de">{avaliado}</span>}
    </span>
  ));
}
