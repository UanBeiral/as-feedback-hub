"use client";

/**
 * Redefinir senha (SCR-0038, segunda metade).
 *
 * O token vem na query do link que chegou por e-mail. Ele não é revalidado antes do
 * envio: uma checagem prévia diria "este link é válido" a quem só o tem, e a validade é
 * exatamente a informação que o link protege. O erro aparece ao tentar usar, que é
 * quando ele custa uma tentativa.
 */

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { Aviso, Botao, Campo, Cartao, Entrada } from "@/components/ui";
import { ApiError, apiVoid } from "@/lib/api";

const MINIMO = 8;

function Formulario() {
  const token = useSearchParams().get("token") ?? "";
  const router = useRouter();
  const [senha, setSenha] = useState("");
  const [repetida, setRepetida] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [pronto, setPronto] = useState(false);

  async function enviar(evento: React.FormEvent) {
    evento.preventDefault();
    setErro(null);
    if (senha !== repetida) {
      setErro("As duas senhas precisam ser iguais.");
      return;
    }
    setEnviando(true);
    try {
      await apiVoid("/auth/reset-password/confirm", {
        method: "POST",
        body: { token, nova_senha: senha },
        publico: true,
      });
      setPronto(true);
    } catch (falha) {
      setErro(
        falha instanceof ApiError
          ? falha.message
          : "Não foi possível redefinir a senha. Peça um link novo.",
      );
    } finally {
      setEnviando(false);
    }
  }

  if (!token) {
    return (
      <div className="space-y-4">
        <Aviso tom="erro">Link incompleto. Abra o endereço exatamente como veio no e-mail.</Aviso>
        <Link
          href="/esqueci-senha"
          className="text-sm text-primary underline-offset-4 hover:underline"
        >
          Pedir um link novo
        </Link>
      </div>
    );
  }

  if (pronto) {
    return (
      <div className="space-y-4">
        <Aviso tom="sucesso">
          Senha alterada. As sessões abertas em outros aparelhos foram encerradas.
        </Aviso>
        <Botao onClick={() => router.replace("/login")} className="w-full">
          Entrar
        </Botao>
      </div>
    );
  }

  return (
    <form onSubmit={enviar} className="space-y-4">
      <Campo rotulo="Nova senha" dica={`No mínimo ${MINIMO} caracteres.`} obrigatorio>
        <Entrada
          type="password"
          value={senha}
          minLength={MINIMO}
          autoComplete="new-password"
          required
          onChange={(evento) => setSenha(evento.target.value)}
        />
      </Campo>
      <Campo rotulo="Repita a nova senha" obrigatorio>
        <Entrada
          type="password"
          value={repetida}
          minLength={MINIMO}
          autoComplete="new-password"
          required
          onChange={(evento) => setRepetida(evento.target.value)}
        />
      </Campo>

      {erro && <Aviso tom="erro">{erro}</Aviso>}

      <Botao tipo="submit" desabilitado={enviando} className="w-full">
        {enviando ? "Salvando…" : "Salvar senha"}
      </Botao>
    </form>
  );
}

export default function RedefinirSenha() {
  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-semibold text-foreground">Nova senha</h1>
        </div>
        <Cartao>
          {/* `useSearchParams` exige limite de Suspense para a página seguir estática. */}
          <Suspense fallback={null}>
            <Formulario />
          </Suspense>
        </Cartao>
      </div>
    </main>
  );
}
