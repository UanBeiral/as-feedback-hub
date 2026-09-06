"use client";

/**
 * Histórico da Equipe — três tipos de feedback, um escopo só.
 *
 * As seções são as mesmas do legado (livre, clientes, 360) e o escopo é o resolvido
 * pelo servidor: gestor vê os liderados, coordenador vê a união, admin vê todos. Nenhum
 * filtro desta tela amplia isso — no máximo restringe o que já veio.
 *
 * O 360 não mostra quem escreveu. Não é omissão de tela: o autor não sai da API, porque
 * o anonimato relativo é o que faz as pessoas escreverem o que pensam.
 *
 * Não há ação de dar ciência aqui: ciência é de quem recebeu o feedback, e o gestor lê a
 * marca sem poder produzi-la. Quem dá ciência faz isso em `/meu-historico`.
 */

import { useEffect, useState } from "react";

import { PaginaAutenticada } from "@/components/pagina";
import { Historico } from "@/components/historico";
import { api } from "@/lib/api";
import type { HistoricoDaEquipe } from "@/lib/tipos";

const VAZIO = { livre: [], clientes: [], ciclos: [] };

export default function HistoricoDaEquipePagina() {
  const [historico, setHistorico] = useState<HistoricoDaEquipe | null>(null);

  useEffect(() => {
    api<HistoricoDaEquipe>("/reports/team-history")
      .then(setHistorico)
      .catch(() => setHistorico(VAZIO));
  }, []);

  return (
    <PaginaAutenticada
      titulo="Histórico da equipe"
      descricao="Feedback livre, avaliações de clientes e ciclos 360 — dentro do seu escopo."
    >
      <Historico
        historico={historico}
        comLinkParaPessoa
        vazio={{
          titulo: "Nenhum histórico encontrado",
          descricao: "Feedbacks aparecem aqui conforme forem enviados para a sua equipe.",
        }}
      />
    </PaginaAutenticada>
  );
}
