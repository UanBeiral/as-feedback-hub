"use client";

/**
 * O formulário de feedback livre (SCR-0023).
 *
 * Mora aqui, e não na tela da equipe, porque **qualquer pessoa** pode escrever para
 * qualquer colega: a API não pede vínculo nenhum, e prender o formulário na tela de quem
 * tem equipe transformava um recurso de todo mundo num recurso de gestor.
 */

import { useState } from "react";

import { AreaDeTexto, Aviso, Botao, Campo, Cartao } from "@/components/ui";
import { ApiError, api } from "@/lib/api";

/**
 * Feedback livre para um membro da equipe (a SCR-0023 do legado, que era um modal).
 *
 * Os três campos são os do legado — pontos positivos, pontos de melhoria e mensagem —,
 * e pelo menos um precisa vir preenchido, que é o que a API cobra. Anônimo **não guarda
 * o autor** (AMB-001): `giver_id` fica nulo no banco, e não escondido na serialização.
 * Por isso o aviso na tela é categórico: depois de enviar não há como voltar atrás.
 */
export function FeedbackLivre({
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
