"use client";

/**
 * Meu Histórico (SCR-0021) — o que escreveram sobre mim.
 *
 * As mesmas três seções do histórico da equipe, com escopo de uma pessoa. Existe como
 * tela separada porque a pergunta é outra: lá o gestor acompanha quem lidera, aqui a
 * pessoa lê o que recebeu — e é o único lugar onde ela **dá ciência**.
 *
 * Ciência é do destinatário. O servidor recusa a marca de quem não é dono do feedback,
 * então o botão só aparece onde a ação existe de verdade; sensível não aparece nem aqui,
 * pela mesma razão de sempre (não chega a quem é o assunto).
 */

import { useCallback, useEffect, useState } from "react";

import { PaginaAutenticada } from "@/components/pagina";
import { Historico } from "@/components/historico";
import { Aviso } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import type { HistoricoDaEquipe, ItemDeHistorico } from "@/lib/tipos";

const VAZIO = { livre: [], clientes: [], ciclos: [] };

export default function MeuHistorico() {
  const [historico, setHistorico] = useState<HistoricoDaEquipe | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    setHistorico(await api<HistoricoDaEquipe>("/reports/my-history").catch(() => VAZIO));
  }, []);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  async function marcarCiente(item: ItemDeHistorico) {
    setErro(null);
    // O caminho depende do tipo porque são dois agregados diferentes, cada um dono do
    // próprio carimbo — uma rota "marcar qualquer coisa como lida" precisaria adivinhar
    // de qual tabela o id veio.
    const caminho =
      item.tipo === "livre"
        ? `/free-feedbacks/${item.item_id}/read`
        : `/requests/${item.item_id}/read`;
    try {
      await api(caminho, { method: "POST" });
      await carregar();
    } catch (falha) {
      setErro(
        falha instanceof ApiError ? falha.message : "Não foi possível registrar a ciência.",
      );
    }
  }

  return (
    <PaginaAutenticada
      titulo="Meu histórico"
      descricao="O feedback que você recebeu — livre, de clientes e dos ciclos 360."
    >
      <div className="space-y-4">
        {erro && <Aviso tom="erro">{erro}</Aviso>}
        <Historico
          historico={historico}
          aoMarcarCiente={marcarCiente}
          vazio={{
            titulo: "Você ainda não recebeu feedback",
            descricao: "O que escreverem sobre você aparece aqui, com data e tipo.",
          }}
        />
      </div>
    </PaginaAutenticada>
  );
}
