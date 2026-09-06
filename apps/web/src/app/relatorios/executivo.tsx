"use client";

/**
 * Emitir Relatório (SCR-0017).
 *
 * O endpoint `POST /reports/executive` existia desde o começo e nenhuma tela o chamava:
 * o relatório executivo — o único que sai em PDF e o único que o legado mandava por
 * e-mail — só era alcançável por `curl`.
 *
 * A validação de escopo é do servidor (BR-MIGRAR-028), e a tela **repete a forma** dela
 * escondendo os campos que não se aplicam. Repetir a regra em `if`s aqui criaria dois
 * lugares para ela mudar; esconder campo não é validar, é não perguntar o que não vale.
 *
 * O PDF vira job no worker (AD-07): a resposta é "pedido registrado", e o arquivo
 * aparece na lista de exportações quando fica pronto. `email_to` é opcional — sem ele o
 * relatório fica só para download, que é o que a maioria dos pedidos quer.
 */

import { useState } from "react";

import { Aviso, Botao, Campo, Cartao, Entrada, Selecao } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import type { Ciclo, Colega } from "@/lib/tipos";

type Escopo = "general" | "person" | "specific";

const ESCOPOS: { valor: Escopo; rotulo: string; explica: string }[] = [
  {
    valor: "general",
    rotulo: "Geral",
    explica: "O escritório inteiro, sem recorte de pessoa.",
  },
  {
    valor: "person",
    rotulo: "Por pessoa",
    explica: "Tudo o que uma pessoa recebeu no ciclo.",
  },
  {
    valor: "specific",
    rotulo: "Específico",
    explica: "O que uma pessoa recebeu de um avaliador em particular.",
  },
];

export function EmitirRelatorio({
  ciclos,
  pessoas,
}: {
  ciclos: Ciclo[];
  pessoas: Colega[];
}) {
  const [escopo, setEscopo] = useState<Escopo>("general");
  const [cicloId, setCicloId] = useState("");
  const [pessoaId, setPessoaId] = useState("");
  const [avaliadorId, setAvaliadorId] = useState("");
  const [email, setEmail] = useState("");
  const [mensagem, setMensagem] = useState<{ tom: "erro" | "sucesso"; texto: string } | null>(
    null,
  );
  const [enviando, setEnviando] = useState(false);

  const escolhido = ESCOPOS.find((e) => e.valor === escopo);
  const pedePessoa = escopo !== "general";
  const pedeAvaliador = escopo === "specific";

  async function emitir(evento: React.FormEvent) {
    evento.preventDefault();
    setMensagem(null);
    setEnviando(true);
    try {
      await api("/reports/executive", {
        method: "POST",
        body: {
          escopo,
          // Campo que o escopo não usa vai como `null`, e não com o resto do que estava
          // digitado: trocar de escopo e deixar um id antigo pendurado é como o legado
          // gerava relatório com recorte que ninguém pediu.
          cycle_id: pedePessoa ? cicloId || null : null,
          profile_id: pedePessoa ? pessoaId || null : null,
          giver_id: pedeAvaliador ? avaliadorId || null : null,
          email_to: email.trim() || null,
        },
      });
      setMensagem({
        tom: "sucesso",
        texto: email.trim()
          ? `Pedido registrado. O PDF vai para ${email.trim()} quando ficar pronto, e também aparece abaixo.`
          : "Pedido registrado. O PDF aparece em «Minhas exportações» quando ficar pronto.",
      });
    } catch (falha) {
      // A mensagem do servidor diz qual campo falta (BR-MIGRAR-028) — repetir a dele
      // evita inventar um texto que discorde da regra.
      setMensagem({
        tom: "erro",
        texto:
          falha instanceof ApiError ? falha.message : "Não foi possível pedir o relatório.",
      });
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Cartao
      titulo="Emitir relatório executivo"
      descricao="Sai em PDF, gerado pelo worker. Pode ir por e-mail junto."
    >
      {mensagem && (
        <div className="mb-4">
          <Aviso tom={mensagem.tom}>{mensagem.texto}</Aviso>
        </div>
      )}

      <form onSubmit={emitir} className="grid gap-4 sm:grid-cols-2">
        <Campo rotulo="Escopo" dica={escolhido?.explica} obrigatorio>
          <Selecao value={escopo} onChange={(e) => setEscopo(e.target.value as Escopo)}>
            {ESCOPOS.map((opcao) => (
              <option key={opcao.valor} value={opcao.valor}>
                {opcao.rotulo}
              </option>
            ))}
          </Selecao>
        </Campo>

        {pedePessoa && (
          <>
            <Campo rotulo="Ciclo" obrigatorio>
              <Selecao required value={cicloId} onChange={(e) => setCicloId(e.target.value)}>
                <option value="">Selecione</option>
                {ciclos.map((ciclo) => (
                  <option key={ciclo.id} value={ciclo.id}>
                    {ciclo.name}
                  </option>
                ))}
              </Selecao>
            </Campo>

            <Campo rotulo="Pessoa avaliada" obrigatorio>
              <Selecao required value={pessoaId} onChange={(e) => setPessoaId(e.target.value)}>
                <option value="">Selecione</option>
                {pessoas.map((pessoa) => (
                  <option key={pessoa.id} value={pessoa.id}>
                    {pessoa.full_name}
                  </option>
                ))}
              </Selecao>
            </Campo>
          </>
        )}

        {pedeAvaliador && (
          <Campo
            rotulo="Avaliador"
            dica="De quem é a avaliação que entra no relatório."
            obrigatorio
          >
            <Selecao
              required
              value={avaliadorId}
              onChange={(e) => setAvaliadorId(e.target.value)}
            >
              <option value="">Selecione</option>
              {pessoas
                .filter((pessoa) => pessoa.id !== pessoaId)
                .map((pessoa) => (
                  <option key={pessoa.id} value={pessoa.id}>
                    {pessoa.full_name}
                  </option>
                ))}
            </Selecao>
          </Campo>
        )}

        <Campo
          rotulo="Enviar por e-mail"
          dica="Opcional. Em branco, o PDF fica só para download."
        >
          <Entrada
            type="email"
            value={email}
            placeholder="socio@escritorio.com.br"
            onChange={(e) => setEmail(e.target.value)}
          />
        </Campo>

        <div className="flex items-end sm:col-span-2">
          <Botao tipo="submit" desabilitado={enviando}>
            {enviando ? "Pedindo…" : "Gerar PDF"}
          </Botao>
        </div>
      </form>
    </Cartao>
  );
}
