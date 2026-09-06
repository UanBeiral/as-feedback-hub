"use client";

/**
 * Minha equipe — uma tela só para gestor, coordenador e administração.
 *
 * No legado eram três (`/gestor/minha-equipe`, `/coordenador/minha-equipe`,
 * `/admin/usuarios` parcial) com a mesma tabela e cálculos de progresso divergentes. O
 * escopo aqui vem inteiro do `TeamScopeService`: gestor vê `manager_id`, coordenador vê
 * a união deduplicada, admin vê todos (BR-MIGRAR-017).
 *
 * A tela é de **acompanhamento**, não de cadastro. Duas contagens diferentes convivem
 * na mesma linha e não devem ser somadas: "a enviar" é o que a pessoa ainda precisa
 * escrever; "a ler" é o que escreveram sobre ela e ela ainda não viu. Num número único,
 * quem já fez a parte dele e só não leu ficaria escondido atrás de quem não fez nada.
 *
 * Todos os números vêm de `/team/progress`, que divide o denominador com o progresso do
 * ciclo (BR-MIGRAR-009) — foi o legado ter três contas diferentes que motivou a regra.
 */

import { useEffect, useState } from "react";

import { PaginaAutenticada } from "@/components/pagina";
import {
  AreaDeTexto,
  Aviso,
  Botao,
  Campo,
  Carregando,
  Cartao,
  Celula,
  EstadoVazio,
  Linha,
  Progresso,
  Selo,
  SeloDePapel,
  Tabela,
} from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { ROTULO_DO_STATUS_DE_PESSOA } from "@/lib/formato";
import { useSessao } from "@/lib/sessao";
import type { AcompanhamentoDaEquipe, PedidoDeEquipe } from "@/lib/tipos";

/** Ação textual dentro de uma linha de tabela. Botão cheio aqui pesaria a tabela. */
function AcaoDeLinha({
  children,
  onClick,
  desabilitado,
  perigo,
}: {
  children: React.ReactNode;
  onClick: () => void;
  desabilitado?: boolean;
  perigo?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={desabilitado}
      className={
        "text-sm underline-offset-4 hover:underline disabled:cursor-not-allowed " +
        "disabled:opacity-50 " +
        (perigo ? "text-destructive" : "text-primary")
      }
    >
      {children}
    </button>
  );
}

/**
 * Feedback livre para um membro da equipe (a SCR-0023 do legado, que era um modal).
 *
 * Os três campos são os do legado — pontos positivos, pontos de melhoria e mensagem —,
 * e pelo menos um precisa vir preenchido, que é o que a API cobra. Anônimo **não guarda
 * o autor** (AMB-001): `giver_id` fica nulo no banco, e não escondido na serialização.
 * Por isso o aviso na tela é categórico: depois de enviar não há como voltar atrás.
 */
function FeedbackLivre({
  para,
  aoFechar,
  aoEnviar,
}: {
  para: { profile_id: string; full_name: string };
  aoFechar: () => void;
  aoEnviar: (texto: string) => void;
}) {
  const [positivos, setPositivos] = useState("");
  const [melhorias, setMelhorias] = useState("");
  const [mensagem, setMensagem] = useState("");
  const [anonimo, setAnonimo] = useState(false);
  const [sensivel, setSensivel] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const vazio = !positivos.trim() && !melhorias.trim() && !mensagem.trim();

  async function enviar(evento: React.FormEvent) {
    evento.preventDefault();
    setErro(null);
    setEnviando(true);
    try {
      await api("/free-feedbacks", {
        method: "POST",
        body: {
          receiver_id: para.profile_id,
          is_anonymous: anonimo,
          is_sensitive: sensivel,
          positives: positivos.trim() || null,
          improvements: melhorias.trim() || null,
          message: mensagem.trim() || null,
        },
      });
      aoEnviar(`Feedback enviado para ${para.full_name}.`);
      aoFechar();
    } catch (falha) {
      setErro(falha instanceof ApiError ? falha.message : "Não foi possível enviar agora.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Cartao
      titulo={`Feedback livre para ${para.full_name}`}
      descricao="Fora do ciclo, a qualquer momento. Preencha o que fizer sentido."
      acao={
        <Botao variante="fantasma" onClick={aoFechar}>
          Fechar
        </Botao>
      }
    >
      <form onSubmit={enviar} className="space-y-4">
        <Campo rotulo="Pontos positivos">
          <AreaDeTexto
            autoFocus
            placeholder="O que essa pessoa fez bem e deveria continuar fazendo."
            value={positivos}
            onChange={(e) => setPositivos(e.target.value)}
          />
        </Campo>
        <Campo rotulo="Pontos de melhoria">
          <AreaDeTexto
            placeholder="O que ela poderia fazer diferente."
            value={melhorias}
            onChange={(e) => setMelhorias(e.target.value)}
          />
        </Campo>
        <Campo rotulo="Mensagem">
          <AreaDeTexto
            placeholder="Algo que não cabe nos dois campos acima."
            value={mensagem}
            onChange={(e) => setMensagem(e.target.value)}
          />
        </Campo>

        <div className="space-y-2">
          <label className="flex items-center gap-2 text-sm text-foreground">
            <input
              type="checkbox"
              checked={anonimo}
              onChange={(e) => setAnonimo(e.target.checked)}
            />
            Enviar anonimamente
          </label>
          <label className="flex items-center gap-2 text-sm text-foreground">
            <input
              type="checkbox"
              checked={sensivel}
              onChange={(e) => setSensivel(e.target.checked)}
            />
            Assunto sensível — só a administração vê
          </label>
          {anonimo && (
            <p className="text-xs text-muted-foreground">
              Seu nome não é guardado em lugar nenhum, nem para a administração. Depois de
              enviar, não há como saber que foi você — inclusive para você.
            </p>
          )}
        </div>

        {erro && <Aviso tom="erro">{erro}</Aviso>}

        <Botao tipo="submit" desabilitado={vazio || enviando}>
          {enviando ? "Enviando…" : "Enviar feedback"}
        </Botao>
      </form>
    </Cartao>
  );
}

/** Estado usado quando a chamada falha: a tela diz "vazio", não fica carregando à toa. */
const SEM_EQUIPE: AcompanhamentoDaEquipe = {
  cycle_id: null,
  cycle_name: null,
  membros: [],
  total_membros: 0,
  enviados: 0,
  esperados: 0,
  percentual: 100,
};

type Membro = AcompanhamentoDaEquipe["membros"][number];

export default function MinhaEquipe() {
  const { usuario } = useSessao();
  const [equipe, setEquipe] = useState<AcompanhamentoDaEquipe | null>(null);
  const [pedidos, setPedidos] = useState<PedidoDeEquipe[]>([]);
  const [aviso, setAviso] = useState<{ tom: "erro" | "sucesso"; texto: string } | null>(null);
  const [feedbackPara, setFeedbackPara] = useState<Membro | null>(null);
  const [lembrando, setLembrando] = useState<string | null>(null);

  // Remover da equipe muda a hierarquia, e no sistema novo isso é ato de admin/RH: são
  // eles que respondem por `PUT /profiles/{id}/manager`. O legado mostrava o X ao
  // gestor; ampliar essa autorização é decisão do cliente, não consequência de copiar
  // um ícone (ver #59 em docs/conferencia-resultado.md).
  const podeRemover = usuario?.role === "admin" || usuario?.role === "rh";

  async function carregar() {
    setEquipe(await api<AcompanhamentoDaEquipe>("/team/progress"));
    try {
      setPedidos(await api<PedidoDeEquipe[]>("/team-requests"));
    } catch {
      // Colaborador comum não tem pedidos para decidir: 403 aqui é esperado e não
      // deve estragar a tela de equipe.
      setPedidos([]);
    }
  }

  useEffect(() => {
    carregar().catch(() => setEquipe(SEM_EQUIPE));
  }, []);

  async function decidir(id: string, acao: "approve" | "reject") {
    setAviso(null);
    try {
      await api(`/team-requests/${id}/${acao}`, {
        method: "POST",
        body: acao === "reject" ? { motivo: null } : undefined,
      });
      await carregar();
    } catch {
      setAviso({ tom: "erro", texto: "Não foi possível concluir agora." });
    }
  }

  async function lembrar(membro: Membro) {
    setAviso(null);
    setLembrando(membro.profile_id);
    try {
      const resposta = await api<{ pendentes: number; mensagem: string }>(
        `/team/${membro.profile_id}/reminder`,
        { method: "POST" },
      );
      // A API distingue "avisei" de "não havia o que avisar"; a tela repassa a
      // diferença em vez de dizer "enviado" nos dois casos.
      setAviso({
        tom: resposta.pendentes > 0 ? "sucesso" : "erro",
        texto:
          resposta.pendentes > 0
            ? `${membro.full_name} foi lembrado(a) — ${resposta.mensagem}`
            : `${membro.full_name} está em dia. ${resposta.mensagem}`,
      });
    } catch (falha) {
      setAviso({
        tom: "erro",
        texto: falha instanceof ApiError ? falha.message : "Não foi possível lembrar agora.",
      });
    } finally {
      setLembrando(null);
    }
  }

  async function removerDaEquipe(membro: Membro) {
    setAviso(null);
    try {
      await api(`/profiles/${membro.profile_id}/manager`, {
        method: "PUT",
        body: { manager_id: null },
      });
      setAviso({
        tom: "sucesso",
        texto: `${membro.full_name} saiu da equipe. A pessoa continua no escritório.`,
      });
      await carregar();
    } catch (falha) {
      setAviso({
        tom: "erro",
        texto: falha instanceof ApiError ? falha.message : "Não foi possível remover agora.",
      });
    }
  }

  return (
    <PaginaAutenticada
      titulo="Minha equipe"
      descricao={
        equipe?.cycle_name
          ? `Como a sua equipe está indo no ciclo ${equipe.cycle_name}. Feedback livre e de clientes ficam no Histórico da equipe.`
          : "Quem está no seu escopo — subordinados diretos e, se você coordena, também os membros coordenados."
      }
    >
      <div className="space-y-6">
        {aviso && <Aviso tom={aviso.tom}>{aviso.texto}</Aviso>}

        {feedbackPara && (
          <FeedbackLivre
            para={feedbackPara}
            aoFechar={() => setFeedbackPara(null)}
            aoEnviar={(texto) => setAviso({ tom: "sucesso", texto })}
          />
        )}

        {pedidos.length > 0 && (
          <Cartao
            titulo="Pedidos de inclusão"
            descricao="Aprovar move a pessoa para a sua equipe."
          >
            <ul className="divide-y divide-border">
              {pedidos.map((pedido) => (
                <li key={pedido.id} className="flex items-center justify-between py-3">
                  <span className="text-sm text-foreground">
                    Inclusão solicitada — aguardando sua decisão
                  </span>
                  <span className="flex gap-2">
                    <Botao onClick={() => void decidir(pedido.id, "approve")}>Aprovar</Botao>
                    <Botao variante="secundario" onClick={() => void decidir(pedido.id, "reject")}>
                      Recusar
                    </Botao>
                  </span>
                </li>
              ))}
            </ul>
          </Cartao>
        )}

        <Cartao titulo="Membros">
          {equipe === null ? (
            <Carregando />
          ) : equipe.membros.length === 0 ? (
            <EstadoVazio
              titulo="Ninguém no seu escopo"
              descricao="Você aparece aqui assim que tiver subordinados ou membros coordenados."
            />
          ) : (
            <>
              {equipe.cycle_id === null && (
                <p className="mb-4 text-sm text-muted-foreground">
                  Nenhum ciclo aberto — as contagens voltam quando o próximo abrir.
                </p>
              )}

              <Tabela
                colunas={[
                  "Nome",
                  "Cargo",
                  "Status",
                  "A enviar",
                  "Enviados",
                  "A ler",
                  "Progresso",
                  "Ações",
                ]}
              >
                {equipe.membros.map((membro) => (
                  <Linha key={membro.profile_id}>
                    <Celula className="font-medium">
                      <span className="flex items-center gap-2">
                        {membro.full_name}
                        {membro.is_coordinator && <SeloDePapel papel={membro.role} coordenador />}
                      </span>
                    </Celula>
                    <Celula>{membro.job_title ?? "—"}</Celula>
                    <Celula>
                      <Selo tom={membro.status === "active" ? "sucesso" : "neutro"}>
                        {ROTULO_DO_STATUS_DE_PESSOA[membro.status] ?? membro.status}
                      </Selo>
                    </Celula>
                    {/* Zero é o caso bom: deixá-lo em cinza faz o olho parar só em quem
                        tem número a resolver. */}
                    <Celula className={membro.pendentes_de_enviar === 0 ? "text-muted-foreground" : ""}>
                      {membro.pendentes_de_enviar}
                    </Celula>
                    <Celula className="text-muted-foreground">{membro.enviados}</Celula>
                    <Celula
                      className={membro.pendentes_de_leitura === 0 ? "text-muted-foreground" : ""}
                    >
                      {membro.pendentes_de_leitura}
                    </Celula>
                    <Celula className="w-48">
                      {/* Quem não tem pedido no ciclo não ganha barra cheia. O serviço
                          trata "0 de 0" como 100% para não dividir por zero, mas na
                          tabela, ao lado de quem tem trabalho de verdade, a barra cheia
                          leria como "está ótimo" quando o caso é "está fora do ciclo". */}
                      {membro.enviados + membro.pendentes_de_enviar === 0 ? (
                        <span className="text-xs text-muted-foreground">fora do ciclo</span>
                      ) : (
                        <Progresso valor={membro.percentual} />
                      )}
                    </Celula>
                    <Celula>
                      <span className="flex items-center gap-3 whitespace-nowrap">
                        <AcaoDeLinha onClick={() => setFeedbackPara(membro)}>
                          Dar feedback
                        </AcaoDeLinha>
                        {/* Lembrar só aparece para quem tem o que responder. Botão que
                            sempre responde "essa pessoa está em dia" é botão que a
                            pessoa aprende a não clicar. */}
                        {membro.pendentes_de_enviar > 0 && (
                          <AcaoDeLinha
                            onClick={() => void lembrar(membro)}
                            desabilitado={lembrando === membro.profile_id}
                          >
                            {lembrando === membro.profile_id ? "Lembrando…" : "Lembrar"}
                          </AcaoDeLinha>
                        )}
                        {podeRemover && (
                          <AcaoDeLinha perigo onClick={() => void removerDaEquipe(membro)}>
                            Remover
                          </AcaoDeLinha>
                        )}
                      </span>
                    </Celula>
                  </Linha>
                ))}
              </Tabela>

              <div className="mt-5 border-t border-border pt-4">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <span className="text-sm font-medium text-foreground">
                    Progresso geral da equipe
                  </span>
                  <span className="text-sm text-muted-foreground">
                    {equipe.enviados} de {equipe.esperados} feedbacks enviados (
                    {equipe.percentual}%)
                  </span>
                </div>
                <div className="mt-2">
                  <Progresso valor={equipe.percentual} />
                </div>
                <p className="mt-3 text-right text-sm text-muted-foreground">
                  Total de membros na equipe: <strong>{equipe.total_membros}</strong>
                </p>
              </div>
            </>
          )}
        </Cartao>
      </div>
    </PaginaAutenticada>
  );
}
