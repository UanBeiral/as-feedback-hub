/** Formatação para exibição. Datas do backend chegam em ISO e saem em pt-BR. */

export function formatarData(iso: string | null | undefined): string {
  if (!iso) return "—";
  const [ano, mes, dia] = iso.slice(0, 10).split("-");
  return `${dia}/${mes}/${ano}`;
}

export function formatarDataHora(iso: string | null | undefined): string {
  if (!iso) return "—";
  const data = new Date(iso);
  return data.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

/** Rótulos de status do request (a máquina de BR-MIGRAR-003). */
export const ROTULO_DO_REQUEST: Record<string, string> = {
  pending: "Pendente",
  draft: "Rascunho",
  submitted: "Enviado",
  expired: "Expirado",
  waived: "Abdicado",
  cancelled: "Cancelado",
};

/** Rótulos do ciclo (BR-MIGRAR-004). */
export const ROTULO_DO_CICLO: Record<string, string> = {
  draft: "Rascunho",
  open: "Aberto",
  closed: "Fechado",
  published: "Publicado",
  archived: "Arquivado",
};
