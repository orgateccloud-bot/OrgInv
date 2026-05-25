import type { Espolio } from "../types";
import {
  getSupabase,
  isSupabaseEnabled,
  type DbBem,
  type DbEspolio,
  type DbHerdeiro,
} from "./supabase";

/** Lista os espólios do usuário logado. */
export async function listarEspolios(): Promise<DbEspolio[]> {
  const sb = getSupabase();
  if (!sb) return [];
  const { data, error } = await sb
    .from("espolio")
    .select("*")
    .order("updated_at", { ascending: false });
  if (error) throw error;
  return data ?? [];
}

/** Carrega um espólio completo (com herdeiros + bens) por id. */
export async function carregarEspolio(id: string): Promise<Espolio | null> {
  const sb = getSupabase();
  if (!sb) return null;

  const [{ data: esp, error: e1 }, { data: herd, error: e2 }, { data: bens, error: e3 }] =
    await Promise.all([
      sb.from("espolio").select("*").eq("id", id).single(),
      sb.from("herdeiro").select("*").eq("espolio_id", id).order("ordem"),
      sb.from("bem").select("*").eq("espolio_id", id).order("ordem"),
    ]);
  if (e1 || e2 || e3) throw e1 || e2 || e3;
  if (!esp) return null;

  return {
    nome: esp.nome,
    cpf_falecido: esp.cpf_falecido ?? "",
    data_obito: esp.data_obito ?? "",
    data_partilha: esp.data_partilha ?? "",
    herdeiros: (herd ?? []).map((h: DbHerdeiro) => ({
      nome: h.nome,
      cpf: h.cpf ?? "",
      fracao_monte: h.fracao_monte ?? 0,
      eh_meeiro: h.eh_meeiro,
    })),
    bens: (bens ?? []).map((b: DbBem) => ({
      identificacao: b.identificacao,
      matricula: b.matricula ?? "",
      municipio: b.municipio ?? undefined,
      regime: (b.regime ?? "Indeterminado — requer classificação") as Espolio["bens"][number]["regime"],
      opcao: (b.opcao ?? "Não aplicável a este regime") as Espolio["bens"][number]["opcao"],
      eh_imovel: b.eh_imovel,
      custo_aquisicao_dirpf: b.custo_aquisicao_dirpf,
      data_aquisicao: b.data_aquisicao,
      valor_partilha: b.valor_partilha,
      valor_venda: b.valor_venda,
      data_operacao: b.data_operacao,
    })),
  };
}

/**
 * Cria ou atualiza um espólio completo (upsert).
 * Se `id` for omitido, cria novo; senão, atualiza.
 * Sempre substitui herdeiros/bens (estratégia delete + insert).
 */
export async function salvarEspolio(
  espolio: Espolio,
  id?: string,
): Promise<string> {
  const sb = getSupabase();
  if (!sb) throw new Error("Supabase não está configurado");

  // Pega o user_id atual
  const { data: { user }, error: userErr } = await sb.auth.getUser();
  if (userErr || !user) throw userErr ?? new Error("Usuário não autenticado");

  const payload = {
    user_id: user.id,
    nome: espolio.nome,
    cpf_falecido: espolio.cpf_falecido || null,
    data_obito: espolio.data_obito || null,
    data_partilha: espolio.data_partilha || null,
  };

  let espolioId: string;
  if (id) {
    const { error } = await sb.from("espolio").update(payload).eq("id", id);
    if (error) throw error;
    espolioId = id;
    // limpa filhos antes de regravar
    await sb.from("herdeiro").delete().eq("espolio_id", espolioId);
    await sb.from("bem").delete().eq("espolio_id", espolioId);
  } else {
    const { data, error } = await sb.from("espolio").insert(payload).select("id").single();
    if (error || !data) throw error ?? new Error("Falha ao criar espólio");
    espolioId = data.id;
  }

  if (espolio.herdeiros.length > 0) {
    const herdRows = espolio.herdeiros.map((h, i) => ({
      espolio_id: espolioId,
      nome: h.nome,
      cpf: h.cpf || null,
      fracao_monte: h.fracao_monte,
      eh_meeiro: h.eh_meeiro,
      ordem: i,
    }));
    const { error } = await sb.from("herdeiro").insert(herdRows);
    if (error) throw error;
  }

  if (espolio.bens.length > 0) {
    const bemRows = espolio.bens.map((b, i) => ({
      espolio_id: espolioId,
      identificacao: b.identificacao,
      matricula: b.matricula || null,
      municipio: b.municipio || null,
      regime: b.regime,
      opcao: b.opcao,
      eh_imovel: b.eh_imovel,
      custo_aquisicao_dirpf: b.custo_aquisicao_dirpf,
      data_aquisicao: b.data_aquisicao,
      valor_partilha: b.valor_partilha,
      valor_venda: b.valor_venda,
      data_operacao: b.data_operacao,
      ordem: i,
    }));
    const { error } = await sb.from("bem").insert(bemRows);
    if (error) throw error;
  }

  return espolioId;
}

/** Apaga um espólio (cascata para herdeiros + bens via FK). */
export async function apagarEspolio(id: string): Promise<void> {
  const sb = getSupabase();
  if (!sb) return;
  const { error } = await sb.from("espolio").delete().eq("id", id);
  if (error) throw error;
}

/** Salva uma extração ou análise de IA no banco para fins de auditoria. */
export async function salvarExtracaoIa(params: {
  espolioId?: string | null;
  documentos: string[];
  resultadoJson: any;
  tokensInput?: number | null;
  tokensOutput?: number | null;
  auditHash?: string | null;
}): Promise<string> {
  const sb = getSupabase();
  if (!sb) throw new Error("Supabase não está configurado");

  const { data: { user }, error: userErr } = await sb.auth.getUser();
  if (userErr || !user) throw userErr ?? new Error("Usuário não autenticado");

  const payload = {
    user_id: user.id,
    espolio_id: params.espolioId || null,
    documentos: params.documentos,
    resultado_json: params.resultadoJson,
    tokens_input: params.tokensInput || null,
    tokens_output: params.tokensOutput || null,
    audit_hash: params.auditHash || null,
  };

  const { data, error } = await sb.from("extracao_ia").insert(payload).select("id").single();
  if (error || !data) throw error ?? new Error("Falha ao salvar auditoria de IA");
  return data.id;
}

/** Re-exporta para componentes que só precisam saber se está ligado. */
export { isSupabaseEnabled };
