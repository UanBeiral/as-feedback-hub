/**
 * 404 (SCR-0041).
 *
 * Sem `use client` e sem `PaginaAutenticada`: esta tela precisa funcionar para quem não
 * tem sessão, e envolvê-la no shell autenticado a mandaria para o login — o que troca
 * "essa página não existe" por "faça login", que é outra resposta e a errada.
 *
 * O link vai para a raiz, que já decide o destino: autenticado vai para o painel do
 * papel, anônimo para o login.
 */

import Link from "next/link";

export default function NaoEncontrada() {
  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <div className="max-w-md text-center">
        <p className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Erro 404
        </p>
        <h1 className="mt-2 text-2xl font-semibold text-foreground">Página não encontrada</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          O endereço não existe, ou o link que você seguiu está desatualizado.
        </p>
        <Link
          href="/"
          className="mt-6 inline-flex h-10 items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:brightness-110"
        >
          Ir para o início
        </Link>
      </div>
    </main>
  );
}
