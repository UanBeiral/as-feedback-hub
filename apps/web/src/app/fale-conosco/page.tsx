"use client";

import { useState } from "react";

import { PaginaAutenticada } from "@/components/pagina";
import {
  AreaDeTexto,
  Aviso,
  Botao,
  Campo,
  Cartao,
  Entrada,
  Selecao,
} from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { useSessao } from "@/lib/sessao";

export default function FaleConosco() {
  const { usuario } = useSessao();
  const [mensagem, setMensagem] = useState<{ tom: "erro" | "sucesso"; texto: string } | null>(null);
  const [formulario, setFormulario] = useState({
    type: "sugestao",
    contact_name: usuario?.full_name ?? "",
    email: usuario?.email ?? "",
    phone: "",
    company: "",
    message: "",
  });

  async function enviar(evento: React.FormEvent) {
    evento.preventDefault();
    setMensagem(null);
    try {
      await api("/contact-messages", {
        method: "POST",
        body: {
          ...formulario,
          phone: formulario.phone || null,
          company: formulario.company || null,
        },
      });
      setFormulario({ ...formulario, message: "" });
      setMensagem({ tom: "sucesso", texto: "Mensagem enviada. Obrigado pelo retorno." });
    } catch (falha) {
      setMensagem({
        tom: "erro",
        texto: falha instanceof ApiError ? falha.message : "Não foi possível enviar agora.",
      });
    }
  }

  return (
    <PaginaAutenticada
      titulo="Fale conosco"
      descricao="Sugestões, problemas e dúvidas sobre o sistema."
    >
      <Cartao>
        <form onSubmit={enviar} className="space-y-4">
          {mensagem && <Aviso tom={mensagem.tom}>{mensagem.texto}</Aviso>}

          <div className="grid gap-4 sm:grid-cols-2">
            <Campo rotulo="Assunto" obrigatorio>
              <Selecao
                value={formulario.type}
                onChange={(e) => setFormulario({ ...formulario, type: e.target.value })}
              >
                <option value="sugestao">Sugestão</option>
                <option value="problema">Problema</option>
                <option value="duvida">Dúvida</option>
              </Selecao>
            </Campo>
            <Campo rotulo="Seu nome" obrigatorio>
              <Entrada
                required
                value={formulario.contact_name}
                onChange={(e) => setFormulario({ ...formulario, contact_name: e.target.value })}
              />
            </Campo>
            <Campo rotulo="E-mail" obrigatorio>
              <Entrada
                type="email"
                required
                value={formulario.email}
                onChange={(e) => setFormulario({ ...formulario, email: e.target.value })}
              />
            </Campo>
            <Campo rotulo="Telefone">
              <Entrada
                value={formulario.phone}
                onChange={(e) => setFormulario({ ...formulario, phone: e.target.value })}
              />
            </Campo>
          </div>

          <Campo rotulo="Mensagem" obrigatorio>
            <AreaDeTexto
              required
              value={formulario.message}
              onChange={(e) => setFormulario({ ...formulario, message: e.target.value })}
            />
          </Campo>

          <Botao tipo="submit">Enviar</Botao>
        </form>
      </Cartao>
    </PaginaAutenticada>
  );
}
