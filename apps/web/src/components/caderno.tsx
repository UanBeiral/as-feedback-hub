"use client";

/**
 * O Caderno do Ciclo (SCR-0022): o widget flutuante que abre **por cima** da tela.
 *
 * A anotação nasce no meio de outra coisa — numa reunião, lendo um relatório, no
 * formulário de feedback —, e um caderno que exige navegar até ele é um caderno que
 * ninguém abre. Por isso é um painel sobre a página, não uma rota: a pessoa anota e
 * volta ao que estava fazendo sem perder nada.
 *
 * Como no legado: usa o ciclo aberto automaticamente (sem ciclo aberto o botão nem
 * aparece), pergunta "Sobre quem?", salva com Ctrl+Enter e aceita ditado pela Web
 * Speech API — que só existe em Chrome/Edge, e o botão diz isso quando não existe.
 *
 * As notas são privadas do autor (a API só devolve as dele), e a lista mostra só as da
 * pessoa escolhida neste ciclo, que é o que se quer ler antes de preencher o feedback.
 */

import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError, api, apiVoid } from "@/lib/api";
import { formatarDataHora } from "@/lib/formato";
import { useSessao } from "@/lib/sessao";
import type { AnotacaoDeCiclo, Ciclo, Perfil } from "@/lib/tipos";

type Reconhecimento = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((evento: { resultIndex: number; results: ArrayLike<ArrayLike<{ transcript: string }> & { isFinal: boolean }> }) => void) | null;
  onend: (() => void) | null;
  onerror: (() => void) | null;
  start: () => void;
  stop: () => void;
};

function criarReconhecimento(): Reconhecimento | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as {
    SpeechRecognition?: new () => Reconhecimento;
    webkitSpeechRecognition?: new () => Reconhecimento;
  };
  const Construtor = w.SpeechRecognition ?? w.webkitSpeechRecognition;
  return Construtor ? new Construtor() : null;
}

export function Caderno({ visivel }: { visivel: boolean }) {
  const { usuario } = useSessao();
  const [aberto, setAberto] = useState(false);
  const [ciclo, setCiclo] = useState<Ciclo | null>(null);
  const [equipe, setEquipe] = useState<Perfil[]>([]);
  const [sobre, setSobre] = useState("");
  const [texto, setTexto] = useState("");
  const [notas, setNotas] = useState<AnotacaoDeCiclo[] | null>(null);
  const [gravando, setGravando] = useState(false);
  const [ditado, setDitado] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const reconhecimento = useRef<Reconhecimento | null>(null);
  const suportaAudio = typeof window !== "undefined" && criarReconhecimento() !== null;

  // O ciclo aberto decide se o caderno existe: sem ciclo não há o que anotar, e o
  // legado escondia o botão nesse caso.
  useEffect(() => {
    if (!visivel || !usuario) return;
    api<Ciclo[]>("/cycles", { query: { status: "open" } })
      .then((ciclos) => setCiclo(ciclos[0] ?? null))
      .catch(() => setCiclo(null));
  }, [visivel, usuario]);

  useEffect(() => {
    if (!aberto || !usuario) return;
    api<Perfil[]>("/auth/my-team")
      .then((membros) =>
        setEquipe(
          membros.filter((m) => m.id !== usuario.profile_id && m.status === "active"),
        ),
      )
      .catch(() => setEquipe([]));
  }, [aberto, usuario]);

  const carregarNotas = useCallback(async () => {
    if (!ciclo) return;
    try {
      const todas = await api<AnotacaoDeCiclo[]>("/cycle-notes", {
        query: { cycle_id: ciclo.id },
      });
      setNotas(todas);
    } catch {
      setNotas([]);
    }
  }, [ciclo]);

  useEffect(() => {
    if (aberto) void carregarNotas();
  }, [aberto, carregarNotas]);

  async function salvar() {
    if (!ciclo || !sobre || !texto.trim() || salvando) return;
    setErro(null);
    setSalvando(true);
    try {
      await api("/cycle-notes", {
        method: "POST",
        body: {
          cycle_id: ciclo.id,
          about_user_id: sobre,
          content: texto.trim(),
          is_audio_transcription: ditado,
        },
      });
      setTexto("");
      setDitado(false);
      await carregarNotas();
    } catch (falha) {
      setErro(falha instanceof ApiError ? falha.message : "Não foi possível salvar a anotação.");
    } finally {
      setSalvando(false);
    }
  }

  async function apagar(id: string) {
    setErro(null);
    try {
      await apiVoid(`/cycle-notes/${id}`, { method: "DELETE" });
      await carregarNotas();
    } catch {
      setErro("Não foi possível apagar.");
    }
  }

  function alternarGravacao() {
    if (gravando) {
      reconhecimento.current?.stop();
      return;
    }
    const r = criarReconhecimento();
    if (!r) return;
    r.lang = "pt-BR";
    r.continuous = true;
    r.interimResults = false;
    r.onresult = (evento) => {
      let final = "";
      for (let i = evento.resultIndex; i < evento.results.length; i += 1) {
        const resultado = evento.results[i];
        if (resultado.isFinal) final += (final ? " " : "") + resultado[0].transcript;
      }
      if (final) {
        setTexto((atual) => (atual ? `${atual} ${final}` : final));
        setDitado(true);
      }
    };
    r.onend = () => setGravando(false);
    r.onerror = () => setGravando(false);
    reconhecimento.current = r;
    r.start();
    setGravando(true);
  }

  if (!visivel || !ciclo) return null;

  const daPessoa = (notas ?? []).filter((n) => n.about_user_id === sobre);
  const nomeDaPessoa = equipe.find((m) => m.id === sobre)?.full_name;

  return (
    <>
      <button
        type="button"
        onClick={() => setAberto((atual) => !atual)}
        title="Caderno do Ciclo"
        aria-expanded={aberto}
        className={
          "fixed bottom-6 right-6 z-30 flex h-12 w-12 items-center justify-center " +
          "rounded-full text-xl shadow-lg transition hover:scale-105 " +
          (aberto ? "bg-primary text-primary-foreground" : "bg-accent text-accent-foreground")
        }
      >
        <span aria-hidden="true">📖</span>
        <span className="sr-only">Caderno do Ciclo</span>
      </button>

      {aberto && (
        <section
          aria-label="Caderno do Ciclo"
          className={
            "fixed bottom-20 left-4 right-4 z-30 flex max-h-[min(520px,calc(100dvh-6.5rem))] " +
            "flex-col overflow-hidden rounded-xl border border-border bg-card shadow-2xl " +
            "sm:left-auto sm:right-6 sm:w-80"
          }
        >
          <header className="flex items-center justify-between gap-2 bg-primary px-4 py-2.5 text-primary-foreground">
            <span className="flex items-center gap-2 text-sm font-semibold">
              <span aria-hidden="true">📖</span> Caderno do Ciclo
              <span
                title="Registre observações ao longo do ciclo para facilitar o preenchimento dos feedbacks. Só você vê as suas anotações."
                className="cursor-help text-xs opacity-80"
              >
                ⓘ
              </span>
            </span>
            <button
              type="button"
              onClick={() => setAberto(false)}
              aria-label="Fechar"
              className="rounded px-1 text-lg leading-none opacity-80 hover:opacity-100"
            >
              ×
            </button>
          </header>
          <p className="border-b border-border bg-muted px-4 py-1.5 text-xs text-muted-foreground">
            {ciclo.name}
          </p>

          <div className="space-y-2 px-4 pt-3">
            <label className="block text-xs font-medium text-foreground">
              Sobre quem?{" "}
              <span title="Selecione a pessoa sobre quem deseja fazer anotações" className="cursor-help text-muted-foreground">
                ⓘ
              </span>
              <select
                value={sobre}
                onChange={(e) => setSobre(e.target.value)}
                className="mt-1 h-9 w-full rounded-md border border-input bg-card px-2 text-sm text-foreground"
              >
                <option value="">Selecione uma pessoa...</option>
                {equipe.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.full_name}
                  </option>
                ))}
              </select>
            </label>

            <textarea
              value={texto}
              onChange={(e) => setTexto(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && e.ctrlKey) {
                  e.preventDefault();
                  void salvar();
                }
              }}
              placeholder="Anote observações, rascunhos ou informações relevantes para o ciclo..."
              title="Registre entregas, comportamentos, situações, pontos positivos ou de melhoria. Ctrl+Enter para salvar."
              rows={3}
              className="w-full resize-none rounded-md border border-input bg-card px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground"
            />

            <div className="flex items-center justify-between gap-2 pb-2">
              <button
                type="button"
                onClick={alternarGravacao}
                disabled={!suportaAudio}
                title={
                  suportaAudio
                    ? gravando
                      ? "Para a gravação e salva o texto transcrito"
                      : "Grave um áudio que será transcrito automaticamente (Chrome/Edge)"
                    : "Ditado por voz só em Chrome/Edge"
                }
                className={
                  "h-8 rounded-md border px-2.5 text-xs " +
                  (gravando
                    ? "border-destructive text-destructive"
                    : "border-border text-foreground hover:bg-muted") +
                  " disabled:cursor-not-allowed disabled:opacity-50"
                }
              >
                {gravando ? "■ Parar" : "🎙 Gravar Áudio"}
              </button>
              <span className="flex items-center gap-2">
                <span className="text-[10px] text-muted-foreground">Ctrl+Enter</span>
                <button
                  type="button"
                  onClick={() => void salvar()}
                  disabled={!sobre || !texto.trim() || salvando}
                  title="Salvar anotação (Ctrl+Enter)"
                  className="h-8 rounded-md bg-primary px-3 text-xs font-medium text-primary-foreground disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {salvando ? "Salvando…" : "➤ Salvar"}
                </button>
              </span>
            </div>
            {erro && <p className="pb-2 text-xs text-destructive">{erro}</p>}
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto border-t border-border px-4 py-3">
            {!sobre ? (
              <p className="py-6 text-center text-xs text-muted-foreground">
                Selecione uma pessoa para ver e criar anotações.
              </p>
            ) : daPessoa.length === 0 ? (
              <div className="py-6 text-center">
                <p className="text-2xl opacity-30" aria-hidden="true">
                  📖
                </p>
                <p className="mt-1 text-sm text-muted-foreground">Nenhuma anotação ainda.</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  💡 Anote ao longo do ciclo para facilitar o preenchimento dos feedbacks!
                </p>
              </div>
            ) : (
              <>
                <p className="mb-2 text-xs font-medium text-foreground">
                  {nomeDaPessoa}{" "}
                  <span className="font-normal text-muted-foreground">
                    · Anotações deste ciclo ({daPessoa.length})
                  </span>
                </p>
                <ul className="space-y-2">
                  {daPessoa.map((nota) => (
                    <li key={nota.id} className="rounded-md bg-muted px-3 py-2">
                      <p className="whitespace-pre-wrap text-sm text-foreground">{nota.content}</p>
                      <p className="mt-1 flex items-center justify-between text-[10px] text-muted-foreground">
                        <span>
                          {formatarDataHora(nota.created_at)}
                          {nota.is_audio_transcription && (
                            <span title="Esta anotação foi transcrita de um áudio"> 🎙️</span>
                          )}
                        </span>
                        <button
                          type="button"
                          onClick={() => void apagar(nota.id)}
                          className="text-destructive hover:underline"
                        >
                          Apagar
                        </button>
                      </p>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>
        </section>
      )}
    </>
  );
}
