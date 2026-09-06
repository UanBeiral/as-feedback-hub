"use client";

/**
 * Esqueci minha senha (SCR-0038, primeira metade).
 *
 * A tela **sempre** diz a mesma coisa: "se existe conta com esse e-mail, o link foi
 * enviado". Responder "não encontramos esse e-mail" transformaria a página num
 * verificador de quem trabalha no escritório, aberto a qualquer um — e não haveria
 * ganho, porque quem tem a conta recebe o e-mail de qualquer jeito.
 */

import Link from "next/link";
import { useState } from "react";

import { Aviso, Botao, Campo, Cartao, Entrada } from "@/components/ui";
import { apiVoid } from "@/lib/api";

export default function EsqueciSenha() {
  const [email, setEmail] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [enviado, setEnviado] = useState(false);

  async function enviar(evento: React.FormEvent) {
    evento.preventDefault();
    setEnviando(true);
    try {
      await apiVoid("/auth/reset-password/request", {
        method: "POST",
        body: { email },
        publico: true,
      });
    } finally {
      // Sucesso mesmo se a chamada falhar por rede: a mensagem não afirma que o e-mail
      // saiu, afirma o que a pessoa deve fazer em seguida. Um erro aqui só a faria
      // tentar de novo achando que errou o endereço.
      setEnviado(true);
      setEnviando(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-semibold text-foreground">Esqueci minha senha</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Mandamos um link para você escolher uma senha nova.
          </p>
        </div>

        <Cartao>
          {enviado ? (
            <div className="space-y-4">
              <Aviso tom="sucesso">
                Se existe uma conta com esse e-mail, o link já está a caminho. Ele vale por
                uma hora e só funciona uma vez.
              </Aviso>
              <p className="text-sm text-muted-foreground">
                Não chegou? Confira a caixa de spam ou tente de novo em alguns minutos.
              </p>
            </div>
          ) : (
            <form onSubmit={enviar} className="space-y-4">
              <Campo rotulo="E-mail" obrigatorio>
                <Entrada
                  type="email"
                  value={email}
                  placeholder="seu@email.com"
                  autoComplete="username"
                  required
                  onChange={(evento) => setEmail(evento.target.value)}
                />
              </Campo>
              <Botao tipo="submit" desabilitado={enviando} className="w-full">
                {enviando ? "Enviando…" : "Enviar link"}
              </Botao>
            </form>
          )}
        </Cartao>

        <p className="mt-4 text-center text-xs text-muted-foreground">
          <Link href="/login" className="text-primary underline-offset-4 hover:underline">
            Voltar para o login
          </Link>
        </p>
      </div>
    </main>
  );
}
