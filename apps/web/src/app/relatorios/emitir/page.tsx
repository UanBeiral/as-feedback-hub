"use client";

/**
 * Emitir Relatório (SCR-0017) — tela própria, com entrada no menu, como no legado.
 *
 * Era uma seção no fim de `/relatorios`; quem procurava "Emitir Relatório" no menu não
 * achava, e quem chegava à seção passava antes por quatro abas de dados que não tinham
 * a ver com o pedido. O formulário é o mesmo; mudou o endereço.
 */

import Link from "next/link";

import { PaginaAutenticada } from "@/components/pagina";

import { EmitirRelatorio } from "../executivo";

export default function EmitirRelatorioPagina() {
  return (
    <PaginaAutenticada
      titulo="Relatório de Feedback"
      descricao="Gere relatórios executivos profissionais para impressão ou PDF."
      acao={
        <Link
          href="/relatorios"
          className="text-sm text-primary underline-offset-4 hover:underline"
        >
          Minhas exportações →
        </Link>
      }
    >
      <EmitirRelatorio />
    </PaginaAutenticada>
  );
}
