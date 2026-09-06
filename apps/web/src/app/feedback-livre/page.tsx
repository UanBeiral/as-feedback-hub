"use client";

/**
 * Dar feedback livre (SCR-0023) — a tela do banner do Início.
 *
 * Existe como tela própria porque o formulário morava em `/minha-equipe`, e ali só chega
 * quem tem equipe. Feedback fora do ciclo é de todo mundo: a API não pede vínculo nenhum
 * entre quem escreve e quem recebe, e prender a entrada na tela do gestor transformava um
 * recurso de todos num recurso de alguns.
 *
 * A escolha da pessoa é **busca com resultado**, e não um `select`: com quarenta nomes o
 * seletor vira rolagem, e é o mesmo motivo pelo qual o legado busca em vez de listar.
 */

import { useEffect, useState } from "react";

import { FeedbackLivre } from "@/components/feedback-livre";
import { PaginaAutenticada } from "@/components/pagina";
import { Aviso, Carregando, Cartao, EstadoVazio, Entrada } from "@/components/ui";
import { api } from "@/lib/api";
import { contemTexto } from "@/lib/exportar";
import type { Colega } from "@/lib/tipos";

export default function DarFeedbackLivre() {
  const [colegas, setColegas] = useState<Colega[] | null>(null);
  const [busca, setBusca] = useState("");
  const [escolhido, setEscolhido] = useState<Colega | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  useEffect(() => {
    api<Colega[]>("/colleagues")
      .then(setColegas)
      .catch(() => setColegas([]));
  }, []);

  const visiveis = (colegas ?? []).filter((colega) =>
    contemTexto(`${colega.full_name} ${colega.job_title ?? ""}`, busca),
  );

  if (escolhido) {
    return (
      <PaginaAutenticada titulo="Dar feedback">
        <div className="space-y-4">
          {aviso && <Aviso tom="sucesso">{aviso}</Aviso>}
          <FeedbackLivre
            para={{ profile_id: escolhido.id, full_name: escolhido.full_name }}
            aoFechar={() => setEscolhido(null)}
            aoEnviar={(texto) => setAviso(texto)}
          />
        </div>
      </PaginaAutenticada>
    );
  }

  return (
    <PaginaAutenticada
      titulo="Dar feedback"
      descricao="Feedback livre para qualquer colega, fora do ciclo, a qualquer momento."
    >
      <div className="space-y-4">
        {aviso && <Aviso tom="sucesso">{aviso}</Aviso>}

        <Cartao titulo="Para quem?">
          {colegas === null ? (
            <Carregando />
          ) : (
            <>
              <Entrada
                type="search"
                autoFocus
                value={busca}
                placeholder="Buscar por nome ou cargo…"
                onChange={(evento) => setBusca(evento.target.value)}
                className="mb-4"
              />
              {visiveis.length === 0 ? (
                <EstadoVazio
                  titulo="Ninguém com esse nome"
                  descricao="A lista traz as pessoas ativas do escritório, menos você."
                />
              ) : (
                <ul className="divide-y divide-border">
                  {visiveis.map((colega) => (
                    <li key={colega.id}>
                      <button
                        type="button"
                        onClick={() => setEscolhido(colega)}
                        className="flex w-full items-center justify-between gap-4 rounded-md px-2 py-2.5 text-left hover:bg-muted"
                      >
                        <span>
                          <span className="block text-sm font-medium text-foreground">
                            {colega.full_name}
                          </span>
                          {colega.job_title && (
                            <span className="block text-xs text-muted-foreground">
                              {colega.job_title}
                            </span>
                          )}
                        </span>
                        <span className="shrink-0 text-sm font-medium text-primary">
                          Escrever
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </Cartao>
      </div>
    </PaginaAutenticada>
  );
}
