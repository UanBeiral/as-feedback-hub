"use client";

import { useCallback, useEffect, useState } from "react";

import { PaginaAutenticada } from "@/components/pagina";
import {
  Aviso,
  Botao,
  Campo,
  Carregando,
  Cartao,
  Celula,
  Entrada,
  EstadoVazio,
  Linha,
  Tabela,
} from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import type { Departamento, Perfil } from "@/lib/tipos";

export default function AdminDepartamentos() {
  const [departamentos, setDepartamentos] = useState<Departamento[] | null>(null);
  const [pessoas, setPessoas] = useState<Perfil[]>([]);
  const [novo, setNovo] = useState("");
  const [editando, setEditando] = useState<{ id: string; nome: string } | null>(null);
  const [mensagem, setMensagem] = useState<{ tom: "erro" | "sucesso"; texto: string } | null>(null);

  const carregar = useCallback(async () => {
    const [lista, perfis] = await Promise.all([
      api<Departamento[]>("/departments"),
      api<Perfil[]>("/profiles"),
    ]);
    setDepartamentos(lista);
    setPessoas(perfis);
  }, []);

  useEffect(() => {
    carregar().catch(() => setDepartamentos([]));
  }, [carregar]);

  function relatar(falha: unknown, padrao: string) {
    setMensagem({ tom: "erro", texto: falha instanceof ApiError ? falha.message : padrao });
  }

  async function criar(evento: React.FormEvent) {
    evento.preventDefault();
    setMensagem(null);
    try {
      await api("/departments", { method: "POST", body: { name: novo } });
      setNovo("");
      await carregar();
    } catch (falha) {
      relatar(falha, "Não foi possível criar.");
    }
  }

  async function renomear() {
    if (!editando) return;
    setMensagem(null);
    try {
      await api(`/departments/${editando.id}`, {
        method: "PUT",
        body: { name: editando.nome },
      });
      setEditando(null);
      await carregar();
    } catch (falha) {
      relatar(falha, "Não foi possível renomear.");
    }
  }

  return (
    <PaginaAutenticada
      titulo="Departamentos"
      descricao="Agrupam as pessoas e alimentam o filtro dos relatórios."
    >
      <div className="space-y-6">
        {mensagem && <Aviso tom={mensagem.tom}>{mensagem.texto}</Aviso>}

        <Cartao titulo="Novo departamento">
          <form onSubmit={criar} className="flex flex-wrap items-end gap-3">
            <div className="min-w-64 flex-1">
              <Campo rotulo="Nome" obrigatorio>
                <Entrada
                  required
                  value={novo}
                  onChange={(e) => setNovo(e.target.value)}
                  placeholder="Cível"
                />
              </Campo>
            </div>
            <Botao tipo="submit">Criar</Botao>
          </form>
        </Cartao>

        <Cartao titulo="Departamentos">
          {departamentos === null ? (
            <Carregando />
          ) : departamentos.length === 0 ? (
            <EstadoVazio titulo="Nenhum departamento" />
          ) : (
            <Tabela colunas={["Nome", "Pessoas", ""]}>
              {departamentos.map((departamento) => {
                const quantas = pessoas.filter(
                  (pessoa) => pessoa.department_id === departamento.id,
                ).length;
                return (
                  <Linha key={departamento.id}>
                    <Celula className="font-medium">
                      {editando?.id === departamento.id ? (
                        <Entrada
                          value={editando.nome}
                          onChange={(e) => setEditando({ ...editando, nome: e.target.value })}
                          className="h-8"
                        />
                      ) : (
                        departamento.name
                      )}
                    </Celula>
                    <Celula className="text-muted-foreground">{quantas}</Celula>
                    <Celula className="text-right">
                      {editando?.id === departamento.id ? (
                        <span className="flex justify-end gap-3">
                          <button
                            type="button"
                            onClick={() => void renomear()}
                            className="text-sm text-primary underline-offset-4 hover:underline"
                          >
                            Salvar
                          </button>
                          <button
                            type="button"
                            onClick={() => setEditando(null)}
                            className="text-sm text-muted-foreground underline-offset-4 hover:underline"
                          >
                            Cancelar
                          </button>
                        </span>
                      ) : (
                        <button
                          type="button"
                          onClick={() =>
                            setEditando({ id: departamento.id, nome: departamento.name })
                          }
                          className="text-sm text-primary underline-offset-4 hover:underline"
                        >
                          Renomear
                        </button>
                      )}
                    </Celula>
                  </Linha>
                );
              })}
            </Tabela>
          )}
        </Cartao>
      </div>
    </PaginaAutenticada>
  );
}
