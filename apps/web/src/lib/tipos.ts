/**
 * Apelidos para os tipos do contrato gerado.
 *
 * Existe para o resto do app escrever `Perfil` em vez de
 * `components["schemas"]["ProfileSummary"]` — e, principalmente, para que uma mudança
 * de nome no backend quebre a compilação **aqui**, em um arquivo, em vez de em trinta
 * componentes.
 */

import type { components } from "./api-schema";

type S = components["schemas"];

export type UsuarioAtual = S["CurrentUser"];
export type Perfil = S["ProfileSummary"];
export type ParDeTokens = S["TokenPair"];
export type Departamento = S["DepartmentOut"];
export type PedidoDeEquipe = S["TeamRequestOut"];

export type Notificacao = S["NotificationOut"];
export type FeedNotificacoes = S["NotificationFeed"];
export type Configuracao = S["SettingOut"];
export type Comunicado = S["PlatformUpdateOut"];
export type MensagemDeContato = S["ContactMessageOut"];

export type Ciclo = S["CycleOut"];
export type Progresso = S["ProgressOut"];
export type Requisicao = S["RequestOut"];
export type RequisicaoDetalhada = S["RequestDetailOut"];
export type Pergunta = S["QuestionOut"];
export type Formulario = S["FormOut"];
export type FeedbackLivre = S["FreeFeedbackOut"];
export type AnotacaoDeCiclo = S["CycleNoteOut"];

export type AvaliacaoDeCliente = S["EvaluationOut"];
export type FormularioPublico = S["PublicFormOut"];
export type PerguntaPublica = S["PublicQuestionOut"];
export type TagDeServico = S["ServiceTagOut"];

export type Linha360 = S["Linha360Out"];
export type LinhaDeCliente = S["LinhaClienteOut"];
export type LinhaDeEngajamento = S["LinhaEngajamentoOut"];
export type JobDeExportacao = S["ExportJobOut"];

export type Papel = "admin" | "rh" | "gestor" | "colaborador";

/** Capacidades individuais (BR-MIGRAR-015). A navegação lê daqui, nunca do papel. */
export type Capacidade = keyof UsuarioAtual["flags"];
