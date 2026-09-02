"use client";

/**
 * Triagem do Fale Conosco.
 *
 * A máquina é `novo → em_andamento → resolvido`, e só ela: reabrir um chamado resolvido
 * não existia no legado, então não foi inventado. Quem precisar, abre outro — e a API
 * recusa a transição com 409, não a tela.
 */

import { useCallback, useEffect, useState } from "react";

import { PaginaAutenticada } from "@/components/pagina";
import {
  Aviso,
  Botao,
  Carregando,
  Cartao,
  EstadoVazio,
  Selo,
} from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { formatarDataHora } from "@/lib/formato";
import type { MensagemDeContato } from "@/lib/tipos";

const TOM = {
  novo: "alerta",
  em_andamento: "destaque",
  resolvido: "sucesso",
} as const;

const ROTULO = {
  novo: "Novo",
  em_andamento: "Em andamento",
  resolvido: "Resolvido",
} as const;

/** As transições que a API aceita — a tela mostra só o que vai dar certo. */
const PROXIMOS: Record<string, { status: string; rotulo: string }[]> = {
  novo: [
    { status: "em_andamento", rotulo: "Assumir" },
    { status: "resolvido", rotulo: "Resolver" },
  ],
  em_andamento: [{ status: "resolvido", rotulo: "Resolver" }],
  resolvido: [],
};

export default function AdminContatos() {
  const [mensagens, setMensagens] = useState<MensagemDeContato[] | null>(null);
  const [filtro, setFiltro] = useState<string>("");
  const [aviso, setAviso] = useState<{ tom: "erro" | "sucesso"; texto: string } | null>(null);

  const carregar = useCallback(async (status: string) => {
    setMensagens(
      await api<MensagemDeContato[]>("/contact-messages", {
        query: status ? { status } : undefined,
      }),
    );
  }, []);

  useEffect(() => {
    carregar(filtro).catch(() => setMensagens([]));
  }, [carregar, filtro]);

  async function mudar(mensagem: MensagemDeContato, status: string) {
    setAviso(null);
    try {
      await api(`/contact-messages/${mensagem.id}`, { method: "PATCH", body: { status } });
      await carregar(filtro);
    } catch (falha) {
      setAviso({
        tom: "erro",
        texto: falha instanceof ApiError ? falha.message : "Não foi possível atualizar.",
      });
    }
  }

  return (
    <PaginaAutenticada
      titulo="Fale conosco — triagem"
      descricao="Sugestões, problemas e dúvidas enviados pelo time."
      acao={
        <span className="flex gap-2">
          {[
            ["", "Todos"],
            ["novo", "Novos"],
            ["em_andamento", "Em andamento"],
            ["resolvido", "Resolvidos"],
          ].map(([valor, rotulo]) => (
            <button
              key={valor || "todos"}
              type="button"
              onClick={() => setFiltro(valor)}
              className={
                "rounded-md px-3 py-1.5 text-sm " +
                (filtro === valor
                  ? "bg-primary text-primary-foreground"
                  : "text-foreground hover:bg-muted")
              }
            >
              {rotulo}
            </button>
          ))}
        </span>
      }
    >
      <div className="space-y-4">
        {aviso && <Aviso tom={aviso.tom}>{aviso.texto}</Aviso>}

        <Cartao>
          {mensagens === null ? (
            <Carregando />
          ) : mensagens.length === 0 ? (
            <EstadoVazio titulo="Nenhuma mensagem" />
          ) : (
            <ul className="divide-y divide-border">
              {mensagens.map((mensagem) => (
                <li key={mensagem.id} className="py-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="flex flex-wrap items-center gap-2 text-sm font-medium text-foreground">
                        {mensagem.contact_name}
                        <Selo tom={TOM[mensagem.status as keyof typeof TOM] ?? "neutro"}>
                          {ROTULO[mensagem.status as keyof typeof ROTULO] ?? mensagem.status}
                        </Selo>
                        <span className="text-xs font-normal text-muted-foreground">
                          {mensagem.type}
                        </span>
                      </p>
                      <p className="mt-1 whitespace-pre-wrap text-sm text-foreground">
                        {mensagem.message}
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {mensagem.email}
                        {mensagem.phone ? ` · ${mensagem.phone}` : ""} ·{" "}
                        {formatarDataHora(mensagem.created_at)}
                      </p>
                    </div>

                    <span className="flex shrink-0 gap-2">
                      {(PROXIMOS[mensagem.status] ?? []).map((acao) => (
                        <Botao
                          key={acao.status}
                          variante="secundario"
                          onClick={() => void mudar(mensagem, acao.status)}
                        >
                          {acao.rotulo}
                        </Botao>
                      ))}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Cartao>
      </div>
    </PaginaAutenticada>
  );
}
