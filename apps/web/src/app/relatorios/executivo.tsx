"use client";

/**
 * Emitir Relatório (SCR-0017), com os campos do legado.
 *
 * **Modo** escolhe o produto: "Detalhado" é o de várias páginas (capa, resumo,
 * detalhamento) e "Resumo" é a folha única para reunião rápida. **Escopo** é a regra de
 * BR-MIGRAR-028: ciclo e pessoa obrigatórios, exceto no geral; o específico exige o
 * avaliador. A validação é do servidor, e a tela **repete a forma** dela escondendo os
 * campos que não se aplicam — esconder campo não é validar, é não perguntar o que não
 * vale.
 *
 * O ciclo aparece também no escopo geral, como no legado ("Geral do Ciclo"), mas fica
 * opcional: a spec deixa o geral sem ciclo de propósito (retrato do escritório inteiro),
 * e quem quer um ciclo só escolhe.
 *
 * O e-mail vem pré-preenchido com o do colaborador quando a lista de perfis está
 * disponível (administração e RH); para os demais papéis a API não expõe e-mail de
 * colega, e o campo fica em branco.
 *
 * O PDF vira job no worker (AD-07): "Baixar PDF" registra o pedido e o arquivo aparece
 * em «Minhas exportações»; "Enviar por email" faz o mesmo e manda o arquivo também.
 */

import { useEffect, useState } from "react";

import { Aviso, Botao, Campo, Cartao, Entrada, Selecao } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import type { Ciclo, Colega, Perfil } from "@/lib/tipos";

type Escopo = "general" | "person" | "specific";
type Modo = "detailed" | "summary";

const MODOS: { valor: Modo; rotulo: string; explica: string }[] = [
  {
    valor: "detailed",
    rotulo: "Detalhado (múltiplas páginas)",
    explica: "Capa + Resumo + Síntese + Detalhamento + Devolutiva",
  },
  { valor: "summary", rotulo: "Resumo (1 folha)", explica: "Condensado em 1 página A4" },
];

const ESCOPOS: { valor: Escopo; rotulo: string; explica: string }[] = [
  {
    valor: "person",
    rotulo: "Individual Completo",
    explica: "Todos os feedbacks de uma pessoa em um ciclo",
  },
  {
    valor: "specific",
    rotulo: "Feedback Específico",
    explica: "Um feedback específico de um avaliador",
  },
  {
    valor: "general",
    rotulo: "Geral do Ciclo",
    explica: "Consolidado de todos os colaboradores",
  },
];

export function EmitirRelatorio() {
  const [ciclos, setCiclos] = useState<Ciclo[]>([]);
  const [pessoas, setPessoas] = useState<Colega[]>([]);
  const [perfis, setPerfis] = useState<Perfil[]>([]);
  const [modo, setModo] = useState<Modo>("detailed");
  const [escopo, setEscopo] = useState<Escopo>("person");
  const [cicloId, setCicloId] = useState("");
  const [pessoaId, setPessoaId] = useState("");
  const [avaliadorId, setAvaliadorId] = useState("");
  const [email, setEmail] = useState("");
  const [emailEditado, setEmailEditado] = useState(false);
  const [mensagem, setMensagem] = useState<{ tom: "erro" | "sucesso"; texto: string } | null>(
    null,
  );
  const [enviando, setEnviando] = useState<"pdf" | "email" | null>(null);

  useEffect(() => {
    api<Ciclo[]>("/cycles")
      .then(setCiclos)
      .catch(() => setCiclos([]));
    // `/colleagues` e não `/profiles`: a lista de nomes basta para o seletor, e a rota de
    // admin recusaria quem tem `can_generate_reports` sem ser admin.
    api<Colega[]>("/colleagues")
      .then(setPessoas)
      .catch(() => setPessoas([]));
    // `/profiles` traz o e-mail e só a administração tem: o 403 aqui é esperado e
    // significa "sem pré-preenchimento", não erro.
    api<Perfil[]>("/profiles")
      .then(setPerfis)
      .catch(() => setPerfis([]));
  }, []);

  // Pré-preenchido com o e-mail do colaborador quando houver um selecionado — e só
  // enquanto a pessoa não tiver digitado outro: prefill que sobrescreve o que foi
  // escrito é pior que campo vazio.
  useEffect(() => {
    if (emailEditado) return;
    const perfil = perfis.find((p) => p.id === pessoaId);
    setEmail(escopo !== "general" && perfil?.email ? perfil.email : "");
  }, [pessoaId, escopo, perfis, emailEditado]);

  const modoEscolhido = MODOS.find((m) => m.valor === modo);
  const escopoEscolhido = ESCOPOS.find((e) => e.valor === escopo);
  const pedePessoa = escopo !== "general";
  const pedeAvaliador = escopo === "specific";
  const podeGerar =
    (!pedePessoa || (cicloId && pessoaId)) && (!pedeAvaliador || avaliadorId) && !enviando;

  async function emitir(comEmail: boolean) {
    setMensagem(null);
    setEnviando(comEmail ? "email" : "pdf");
    try {
      await api("/reports/executive", {
        method: "POST",
        body: {
          escopo,
          modo,
          // Campo que o escopo não usa vai como `null`, e não com o resto do que estava
          // digitado: trocar de escopo e deixar um id antigo pendurado é como o legado
          // gerava relatório com recorte que ninguém pediu.
          cycle_id: cicloId || null,
          profile_id: pedePessoa ? pessoaId || null : null,
          giver_id: pedeAvaliador ? avaliadorId || null : null,
          email_to: comEmail ? email.trim() || null : null,
        },
      });
      setMensagem({
        tom: "sucesso",
        texto: comEmail
          ? `Pedido registrado. O PDF vai para ${email.trim()} quando ficar pronto, e também aparece em «Minhas exportações».`
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
      setEnviando(null);
    }
  }

  return (
    <div className="space-y-6">
      <Cartao>
        {mensagem && (
          <div className="mb-4">
            <Aviso tom={mensagem.tom}>{mensagem.texto}</Aviso>
          </div>
        )}

        <div className="grid gap-4 sm:grid-cols-2">
          <Campo rotulo="Modo" dica={modoEscolhido?.explica}>
            <Selecao value={modo} onChange={(e) => setModo(e.target.value as Modo)}>
              {MODOS.map((opcao) => (
                <option key={opcao.valor} value={opcao.valor}>
                  {opcao.rotulo}
                </option>
              ))}
            </Selecao>
          </Campo>

          <Campo rotulo="Escopo" dica={escopoEscolhido?.explica}>
            <Selecao
              value={escopo}
              onChange={(e) => {
                setEscopo(e.target.value as Escopo);
                setAvaliadorId("");
              }}
            >
              {ESCOPOS.map((opcao) => (
                <option key={opcao.valor} value={opcao.valor}>
                  {opcao.rotulo}
                </option>
              ))}
            </Selecao>
          </Campo>

          {pedePessoa && (
            <Campo rotulo="Colaborador" obrigatorio>
              <Selecao required value={pessoaId} onChange={(e) => setPessoaId(e.target.value)}>
                <option value="">Selecione...</option>
                {pessoas.map((pessoa) => (
                  <option key={pessoa.id} value={pessoa.id}>
                    {pessoa.full_name}
                  </option>
                ))}
              </Selecao>
            </Campo>
          )}

          <Campo
            rotulo="Ciclo"
            obrigatorio={pedePessoa}
            dica={pedePessoa ? undefined : "Em branco, consolida todos os ciclos."}
          >
            <Selecao required={pedePessoa} value={cicloId} onChange={(e) => setCicloId(e.target.value)}>
              <option value="">Selecione...</option>
              {ciclos.map((ciclo) => (
                <option key={ciclo.id} value={ciclo.id}>
                  {ciclo.name}
                </option>
              ))}
            </Selecao>
          </Campo>

          {pedeAvaliador && (
            <Campo rotulo="Avaliador" obrigatorio>
              <Selecao required value={avaliadorId} onChange={(e) => setAvaliadorId(e.target.value)}>
                <option value="">Selecione...</option>
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

          <div className="sm:col-span-2">
            <Campo
              rotulo="Email do relatório"
              dica="Pré-preenchido com o email do colaborador quando houver um selecionado."
            >
              <Entrada
                type="email"
                value={email}
                placeholder="email@exemplo.com"
                onChange={(e) => {
                  setEmail(e.target.value);
                  setEmailEditado(true);
                }}
              />
            </Campo>
          </div>
        </div>

        <div className="mt-5 flex flex-wrap gap-3">
          <Botao onClick={() => void emitir(false)} desabilitado={!podeGerar}>
            {enviando === "pdf" ? "Gerando PDF..." : "⤓ Baixar PDF"}
          </Botao>
          <Botao
            variante="secundario"
            onClick={() => void emitir(true)}
            desabilitado={!podeGerar || !email.trim()}
          >
            {enviando === "email" ? "Enviando..." : "✉ Enviar por email"}
          </Botao>
        </div>
      </Cartao>

      <Cartao titulo="Sobre os relatórios">
        <dl className="space-y-2 text-sm">
          <div>
            <dt className="font-medium text-foreground">Detalhado:</dt>
            <dd className="text-muted-foreground">
              Capa, resumo com selo de classificação, síntese gerencial com análise consolidada e
              perspectivas por tipo, detalhamento agrupado, nuvem de temas e termo de devolutiva.
            </dd>
          </div>
          <div>
            <dt className="font-medium text-foreground">Resumo:</dt>
            <dd className="text-muted-foreground">1 folha A4 para reuniões rápidas e arquivamento.</dd>
          </div>
        </dl>
      </Cartao>
    </div>
  );
}
