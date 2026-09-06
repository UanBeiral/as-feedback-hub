"use client";

/**
 * Filtro e ordenação de tabela, do lado do cliente.
 *
 * Estas telas carregam a lista inteira (o escritório tem dezenas de pessoas, não
 * milhares), então filtrar no navegador é instantâneo e não gasta ida ao servidor a cada
 * tecla. **Não é o padrão para tudo**: Relatórios pagina no servidor porque lá o volume é
 * outro, e o dia em que uma destas tabelas passar de alguns milhares de linhas, o certo é
 * mover o filtro para a API — não aumentar o limite da consulta.
 *
 * O hook devolve a lista já filtrada e ordenada, mais o que a barra de filtros e os
 * cabeçalhos clicáveis precisam. Quem usa não repete `useState` de busca, de direção e de
 * campo em cada página.
 */

import { useState } from "react";

import { contemTexto, ordenarPor } from "./exportar";

export type Filtro<T> = {
  /** Valor atual do seletor; `""` significa "todos". */
  valor: string;
  aoMudar: (valor: string) => void;
  /** Decide se o item passa. Só é chamado quando há valor escolhido. */
  aplica: (item: T, valor: string) => boolean;
};

export function useTabela<T>(
  itens: T[],
  opcoes: {
    /** Campos varridos pela busca livre. */
    busca: (item: T) => (string | null | undefined)[];
    /** Como cada campo ordenável é lido. A chave é o `campo` da coluna. */
    campos: Record<string, (item: T) => unknown>;
    /** Ordenação inicial. Sem ela, a lista fica na ordem que a API mandou. */
    inicial?: { campo: string; direcao?: "asc" | "desc" };
  },
) {
  const [busca, setBusca] = useState("");
  const [campo, setCampo] = useState<string | null>(opcoes.inicial?.campo ?? null);
  const [direcao, setDirecao] = useState<"asc" | "desc">(opcoes.inicial?.direcao ?? "asc");
  const [filtros, setFiltros] = useState<Record<string, string>>({});

  function aoOrdenar(novo: string) {
    // Clicar de novo na mesma coluna inverte; clicar noutra começa crescente. É o que a
    // pessoa espera de qualquer tabela, e o que evita a surpresa de mudar de coluna e
    // receber a ordem decrescente que ficou da anterior.
    if (novo === campo) {
      setDirecao((atual) => (atual === "asc" ? "desc" : "asc"));
    } else {
      setCampo(novo);
      setDirecao("asc");
    }
  }

  function filtro(chave: string, aplica: (item: T, valor: string) => boolean): Filtro<T> {
    return {
      valor: filtros[chave] ?? "",
      aoMudar: (valor) => setFiltros((atual) => ({ ...atual, [chave]: valor })),
      aplica,
    };
  }

  function visiveis(ativos: Filtro<T>[] = []): T[] {
    const filtrados = itens.filter(
      (item) =>
        opcoes.busca(item).some((texto) => contemTexto(texto, busca)) &&
        ativos.every((f) => !f.valor || f.aplica(item, f.valor)),
    );
    if (campo === null) return filtrados;
    const ler = opcoes.campos[campo];
    return ler ? ordenarPor(filtrados, ler, direcao) : filtrados;
  }

  return {
    busca,
    setBusca,
    ordenacao: { campo, direcao, aoOrdenar },
    filtro,
    visiveis,
    total: itens.length,
  };
}
