/**
 * Client HTTP tipado pelo contrato OpenAPI (AD-08).
 *
 * Os tipos vêm de `api-schema.d.ts`, gerado por `npm run gen:api` a partir do
 * `openapi.json` que a própria API exporta. Nada aqui é escrito à mão: redefinir
 * modelos no front foi o que levou o legado a espalhar `as any` quando os tipos do
 * Supabase ficaram desatualizados (BR-DESCARTAR-004).
 *
 * O client também concentra a renovação de sessão. Quando a API responde 401, ele
 * tenta **uma vez** trocar o refresh token por um novo par e repete a requisição. Uma
 * vez, e não em laço: se a renovação falhar, insistir só transforma sessão expirada em
 * tempestade de requisições.
 */

import type { paths } from "./api-schema";

export type Rotas = paths;

/** Erro de domínio da API, no formato único de `core/errors.py`. */
export type ErroDaApi = {
  code: string;
  message: string;
  details?: Record<string, unknown>;
};

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown>;

  constructor(status: number, corpo: Partial<ErroDaApi>) {
    super(corpo.message ?? "Erro inesperado");
    this.status = status;
    this.code = corpo.code ?? "unknown";
    this.details = corpo.details ?? {};
  }

  /** 422 do Pydantic não vem no formato de domínio; normalizamos a leitura. */
  get ehValidacao(): boolean {
    return this.status === 422;
  }
}

const CHAVE_REFRESH = "asfeedback.refresh";

/**
 * O access token fica **em memória**, e só o refresh vai para o storage.
 *
 * É a divisão que limita o estrago de um XSS: o token de uso imediato morre quando a
 * aba fecha, e o de longa duração é de uso único e rotativo (AD-03) — reapresentá-lo
 * derruba a sessão inteira, o que torna o roubo detectável.
 */
let accessToken: string | null = null;

export const sessao = {
  definir(access: string, refresh: string) {
    accessToken = access;
    localStorage.setItem(CHAVE_REFRESH, refresh);
  },
  definirAccess(access: string) {
    accessToken = access;
  },
  limpar() {
    accessToken = null;
    localStorage.removeItem(CHAVE_REFRESH);
  },
  get access() {
    return accessToken;
  },
  get refresh() {
    return typeof window === "undefined" ? null : localStorage.getItem(CHAVE_REFRESH);
  },
};

async function renovar(): Promise<boolean> {
  const refresh = sessao.refresh;
  if (!refresh) return false;

  const resposta = await fetch("/api/v1/auth/refresh", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });

  if (!resposta.ok) {
    sessao.limpar();
    return false;
  }

  const par = (await resposta.json()) as { access_token: string; refresh_token: string };
  sessao.definir(par.access_token, par.refresh_token);
  return true;
}

type Opcoes = {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  query?: Record<string, string | number | boolean | undefined | null>;
  /** Rotas públicas (`/public/...`) não mandam credencial nem tentam renovar. */
  publico?: boolean;
};

function comQuery(caminho: string, query: Opcoes["query"]): string {
  if (!query) return caminho;
  const params = new URLSearchParams();
  for (const [chave, valor] of Object.entries(query)) {
    if (valor !== undefined && valor !== null && valor !== "") params.set(chave, String(valor));
  }
  const texto = params.toString();
  return texto ? `${caminho}?${texto}` : caminho;
}

async function executar(caminho: string, opcoes: Opcoes, jaRenovou: boolean): Promise<Response> {
  const cabecalhos: Record<string, string> = {};
  if (opcoes.body !== undefined) cabecalhos["content-type"] = "application/json";
  if (!opcoes.publico && sessao.access) {
    cabecalhos.authorization = `Bearer ${sessao.access}`;
  }

  const resposta = await fetch(comQuery(`/api/v1${caminho}`, opcoes.query), {
    method: opcoes.method ?? "GET",
    headers: cabecalhos,
    body: opcoes.body === undefined ? undefined : JSON.stringify(opcoes.body),
  });

  if (resposta.status === 401 && !opcoes.publico && !jaRenovou && (await renovar())) {
    return executar(caminho, opcoes, true);
  }
  return resposta;
}

/** Chamada que devolve corpo JSON. Lança `ApiError` em qualquer status ≥ 400. */
export async function api<T>(caminho: string, opcoes: Opcoes = {}): Promise<T> {
  const resposta = await executar(caminho, opcoes, false);
  if (!resposta.ok) throw await erroDe(resposta);
  if (resposta.status === 204) return undefined as T;
  return (await resposta.json()) as T;
}

/** Chamada sem corpo de resposta (204). */
export async function apiVoid(caminho: string, opcoes: Opcoes = {}): Promise<void> {
  const resposta = await executar(caminho, opcoes, false);
  if (!resposta.ok) throw await erroDe(resposta);
}

/** Download de arquivo gerado pelo worker (AD-07): precisa do Bearer, então não é <a>. */
export async function apiBlob(caminho: string): Promise<Blob> {
  const resposta = await executar(caminho, {}, false);
  if (!resposta.ok) throw await erroDe(resposta);
  return resposta.blob();
}

async function erroDe(resposta: Response): Promise<ApiError> {
  let corpo: Partial<ErroDaApi> = {};
  try {
    const json = (await resposta.json()) as Record<string, unknown>;
    corpo = {
      code: typeof json.code === "string" ? json.code : undefined,
      message:
        typeof json.message === "string"
          ? json.message
          : // 422 do FastAPI vem como `detail`, que é lista de problemas por campo.
            Array.isArray(json.detail)
            ? "Dados inválidos no formulário"
            : typeof json.detail === "string"
              ? json.detail
              : undefined,
      details: (json.details as Record<string, unknown>) ?? undefined,
    };
  } catch {
    // Resposta sem JSON (502 do proxy, por exemplo): a mensagem padrão serve.
  }
  return new ApiError(resposta.status, corpo);
}
