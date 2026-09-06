"use client";

/**
 * Uma aba de relatório: filtros, escolha de colunas, ordenação, contador e exportação.
 *
 * As quatro abas (360, clientes, livres, engajamento) mostram a mesma coisa com dados
 * diferentes — uma tabela agregada por pessoa. Escrever as quatro à mão foi o que fez a
 * tela nascer sem filtro, sem ordenação e sem contador: cada melhoria custava quatro
 * edições, e por isso nenhuma acontecia. Aqui é um componente só, e o que vale para uma
 * aba vale para as quatro.
 *
 * A coluna é declarada com `valor` (o que ordena e o que vai para o CSV) e, quando o
 * visual não é o valor cru, `celula`. Manter os dois separados é o que impede o CSV de
 * sair com "—" no lugar de vazio, ou com uma barra de progresso virando `[object Object]`.
 */

import { useState, type ReactNode } from "react";

import {
  Botao,
  BotaoDeExportar,
  BarraDeFiltros,
  Carregando,
  Cartao,
  Celula,
  ContadorDeResultados,
  EstadoVazio,
  Linha,
  SeletorDeColunas,
  Tabela,
} from "@/components/ui";
import { exportarCsv } from "@/lib/exportar";
import { useTabela } from "@/lib/tabela";

export type ColunaDeRelatorio<T> = {
  /** Identifica a coluna na ordenação e no seletor de colunas. */
  chave: string;
  rotulo: string;
  /** O que ordena e o que vai para o CSV. */
  valor: (item: T) => string | number | null;
  /** O que aparece na célula, quando não é o valor cru. */
  celula?: (item: T) => ReactNode;
  className?: string;
  /** Coluna que identifica a linha: não pode ser desligada. */
  fixa?: boolean;
};

export function AbaDeRelatorio<T>({
  titulo,
  descricao,
  itens,
  chaveDe,
  colunas,
  buscaPor,
  placeholder = "Buscar pessoa…",
  arquivo,
  vazio,
  filtros,
  formatos = [],
}: {
  titulo: string;
  descricao?: string;
  /** `null` enquanto carrega. */
  itens: T[] | null;
  chaveDe: (item: T) => string;
  colunas: ColunaDeRelatorio<T>[];
  buscaPor: (item: T) => (string | null | undefined)[];
  placeholder?: string;
  /** Nome do arquivo CSV, sem extensão. */
  arquivo: string;
  vazio: { titulo: string; descricao?: string };
  /** Controles que refazem a consulta no servidor (ciclo, departamento, período). */
  filtros?: ReactNode;
  /** Exportações que viram job no worker. */
  formatos?: { rotulo: string; aoConfirmar: () => void | Promise<void> }[];
}) {
  const [ocultas, setOcultas] = useState<string[]>([]);
  const [previa, setPrevia] = useState<{
    rotulo: string;
    aoConfirmar: () => void | Promise<void>;
  } | null>(null);

  const tabela = useTabela(itens ?? [], {
    busca: buscaPor,
    campos: Object.fromEntries(colunas.map((c) => [c.chave, c.valor])),
    inicial: { campo: colunas[0]?.chave ?? "" },
  });
  const visiveis = tabela.visiveis();
  const mostradas = colunas.filter((c) => c.fixa || !ocultas.includes(c.chave));

  function exportar() {
    exportarCsv(
      arquivo,
      mostradas.map((c) => c.rotulo),
      visiveis.map((item) => mostradas.map((c) => c.valor(item))),
    );
  }

  return (
    <Cartao titulo={titulo} descricao={descricao}>
      {itens === null ? (
        <Carregando />
      ) : itens.length === 0 ? (
        <EstadoVazio titulo={vazio.titulo} descricao={vazio.descricao} />
      ) : (
        <>
          <BarraDeFiltros
            busca={tabela.busca}
            aoBuscar={tabela.setBusca}
            placeholder={placeholder}
            acoes={
              <>
                <ContadorDeResultados mostrando={visiveis.length} total={itens.length} />
                <SeletorDeColunas
                  colunas={colunas.map((c) => ({
                    chave: c.chave,
                    rotulo: c.rotulo,
                    fixa: c.fixa,
                  }))}
                  ocultas={ocultas}
                  aoAlternar={(chave) =>
                    setOcultas((atual) =>
                      atual.includes(chave)
                        ? atual.filter((c) => c !== chave)
                        : [...atual, chave],
                    )
                  }
                />
                <BotaoDeExportar quantidade={visiveis.length} onClick={exportar} />
                {formatos.map((formato) => (
                  <Botao
                    key={formato.rotulo}
                    variante="fantasma"
                    onClick={() => setPrevia(formato)}
                  >
                    {formato.rotulo}
                  </Botao>
                ))}
              </>
            }
          >
            {filtros}
          </BarraDeFiltros>

          {previa && (
            // A prévia sai das linhas já carregadas, não de uma segunda consulta: a
            // tabela na tela nasceu destes mesmos filtros, então perguntar de novo ao
            // servidor só adicionaria a chance de as duas respostas discordarem.
            <div className="mb-4 rounded-md border border-border bg-muted/40 p-4">
              <p className="text-sm font-medium text-foreground">
                Prévia — {visiveis.length} linha{visiveis.length === 1 ? "" : "s"} com os
                filtros atuais
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                Colunas: {mostradas.map((c) => c.rotulo).join(", ")}
              </p>
              <ul className="mt-3 space-y-1 text-xs text-muted-foreground">
                {visiveis.slice(0, 5).map((item) => (
                  <li key={chaveDe(item)}>
                    {mostradas.map((c) => c.valor(item) ?? "—").join(" · ")}
                  </li>
                ))}
                {visiveis.length > 5 && <li>…e mais {visiveis.length - 5}.</li>}
              </ul>
              <div className="mt-4 flex gap-2">
                <Botao
                  onClick={() => {
                    void previa.aoConfirmar();
                    setPrevia(null);
                  }}
                >
                  Gerar
                </Botao>
                <Botao variante="fantasma" onClick={() => setPrevia(null)}>
                  Cancelar
                </Botao>
              </div>
            </div>
          )}

          <Tabela
            ordenacao={tabela.ordenacao}
            vazio={visiveis.length === 0}
            vazioTexto="Nenhuma linha com esses filtros."
            colunas={mostradas.map((c) => ({ rotulo: c.rotulo, campo: c.chave }))}
          >
            {visiveis.map((item) => (
              <Linha key={chaveDe(item)}>
                {mostradas.map((coluna) => (
                  <Celula key={coluna.chave} className={coluna.className}>
                    {coluna.celula ? coluna.celula(item) : (coluna.valor(item) ?? "—")}
                  </Celula>
                ))}
              </Linha>
            ))}
          </Tabela>
        </>
      )}
    </Cartao>
  );
}
