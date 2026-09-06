"use client";

/**
 * Histórico por Pessoa (SCR-0037).
 *
 * O mesmo componente do histórico da equipe com escopo de uma pessoa. Existe porque o
 * filtro por nome resolve com quatro liderados e deixa de resolver com trinta: a pergunta
 * "o que aconteceu com a Bruna neste ano" não se responde rolando uma lista de todos.
 *
 * Sem ação de dar ciência: ciência é de quem recebeu o feedback, e aqui quem lê é a
 * gestão olhando outra pessoa. Quem dá ciência faz isso em `/meu-historico`.
 *
 * Pessoa fora do escopo devolve 404 no servidor, e a tela repete isso sem inventar
 * explicação — dizer "você não tem permissão" já confirmaria que ela existe.
 */

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { Historico } from "@/components/historico";
import { PaginaAutenticada } from "@/components/pagina";
import { Cartao, EstadoVazio } from "@/components/ui";
import { api } from "@/lib/api";
import type { Colega, HistoricoDaEquipe } from "@/lib/tipos";

export default function HistoricoDaPessoa() {
  const { id } = useParams<{ id: string }>();
  const [historico, setHistorico] = useState<HistoricoDaEquipe | null>(null);
  const [nome, setNome] = useState<string | null>(null);
  const [semAcesso, setSemAcesso] = useState(false);

  useEffect(() => {
    api<HistoricoDaEquipe>(`/reports/history/person/${id}`)
      .then(setHistorico)
      .catch(() => setSemAcesso(true));
    // O nome vem da lista de colegas, e não de uma rota de perfil por id: é uma consulta
    // que a tela já sabe fazer, e um endpoint a menos para autorizar.
    api<Colega[]>("/colleagues")
      .then((colegas) => setNome(colegas.find((c) => c.id === id)?.full_name ?? null))
      .catch(() => setNome(null));
  }, [id]);

  if (semAcesso) {
    return (
      <PaginaAutenticada titulo="Histórico">
        <Cartao>
          <EstadoVazio
            titulo="Pessoa não encontrada no seu escopo"
            descricao="Você vê o histórico de quem lidera ou coordena."
          />
          <Voltar />
        </Cartao>
      </PaginaAutenticada>
    );
  }

  return (
    <PaginaAutenticada
      titulo={nome ? `Histórico de ${nome}` : "Histórico"}
      descricao="Feedback livre, avaliações de clientes e ciclos 360 desta pessoa."
    >
      <div className="space-y-4">
        <Historico
          historico={historico}
          vazio={{
            titulo: "Nada registrado ainda",
            descricao: "Feedbacks aparecem aqui conforme forem enviados para esta pessoa.",
          }}
        />
        <Voltar />
      </div>
    </PaginaAutenticada>
  );
}

function Voltar() {
  return (
    <Link
      href="/historico-equipe"
      className="text-sm font-medium text-primary underline-offset-4 hover:underline"
    >
      ← Voltar para o histórico da equipe
    </Link>
  );
}
