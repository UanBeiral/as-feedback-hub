/**
 * Exportação de tabela para CSV, no navegador.
 *
 * As exportações pesadas — relatório executivo, XLSX, PDF — são job do worker (AD-07),
 * porque montam dados que a tela não tem. Estas aqui são o oposto: a tabela **já está
 * carregada**, e mandá-la de volta ao servidor para receber de volta o que o navegador
 * tem em memória seria uma viagem sem propósito.
 *
 * Há um ganho que não é só de latência: exportar da tela garante que o arquivo é o que
 * a pessoa está vendo, com os filtros que ela aplicou. É o que `target_screens.md` pede
 * em `reflects_filters: true`, e é o comportamento que um relatório gerado no servidor
 * com "os mesmos filtros" erra na primeira divergência entre as duas implementações.
 */

/** Separador `;` e CRLF, como em `reporting/service.py` (BR-MIGRAR-029). */
const SEPARADOR = ";";

/**
 * Escapa um valor para CSV.
 *
 * O `=` no começo entra na lista porque Excel e LibreOffice tratam uma célula iniciada
 * por `=`, `+`, `-` ou `@` como **fórmula**. Um nome de departamento que comece com `-`
 * viraria erro de cálculo na planilha, e um valor vindo de campo livre viraria vetor de
 * injeção de fórmula. Prefixar com aspa simples é a defesa padrão.
 */
function celula(valor: unknown): string {
  if (valor === null || valor === undefined) return "";
  const texto = String(valor);
  const perigoso = /^[=+\-@]/.test(texto);
  const bruto = perigoso ? `'${texto}` : texto;
  return /[";\r\n]/.test(bruto) ? `"${bruto.replaceAll('"', '""')}"` : bruto;
}

/**
 * Monta o CSV e dispara o download.
 *
 * O BOM (`﻿`) no início não é enfeite: sem ele o Excel em português abre o arquivo
 * em Latin-1 e todo acento vira caractere quebrado — que é a primeira coisa que alguém
 * reclama de uma exportação.
 */
export function exportarCsv(
  nomeDoArquivo: string,
  cabecalho: string[],
  linhas: unknown[][],
): void {
  const conteudo =
    "﻿" +
    [cabecalho, ...linhas].map((linha) => linha.map(celula).join(SEPARADOR)).join("\r\n");

  const blob = new Blob([conteudo], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${nomeDoArquivo}-${new Date().toISOString().slice(0, 10)}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

/**
 * Compara dois valores para ordenação, com as regras que uma tabela em português pede.
 *
 * `localeCompare` com `sensitivity: "base"` é o que faz "Ávila" cair entre "Avila" e
 * "Azevedo" em vez de ir para o fim da lista, que é onde a comparação por código de
 * caractere o colocaria. Nulos vão sempre para o fim, independentemente da direção:
 * "sem cargo" no topo da lista ordenada por cargo não ajuda ninguém.
 */
export function comparar(a: unknown, b: unknown): number {
  const aVazio = a === null || a === undefined || a === "";
  const bVazio = b === null || b === undefined || b === "";
  if (aVazio && bVazio) return 0;
  if (aVazio) return 1;
  if (bVazio) return -1;

  if (typeof a === "number" && typeof b === "number") return a - b;
  return String(a).localeCompare(String(b), "pt-BR", { sensitivity: "base", numeric: true });
}

/** Ordena uma cópia, para não mexer no array que veio da API. */
export function ordenarPor<T>(
  itens: T[],
  campo: (item: T) => unknown,
  direcao: "asc" | "desc",
): T[] {
  const sinal = direcao === "asc" ? 1 : -1;
  return [...itens].sort((a, b) => comparar(campo(a), campo(b)) * sinal);
}

/** Busca sem acento e sem caixa — "Antonio" acha "Antônio". */
export function contemTexto(alvo: string | null | undefined, busca: string): boolean {
  if (!busca.trim()) return true;
  const normalizar = (texto: string) =>
    texto
      .normalize("NFD")
      .replace(/\p{Diacritic}/gu, "")
      .toLowerCase();
  return normalizar(alvo ?? "").includes(normalizar(busca));
}
