import { createClient, type SupabaseClient } from "@supabase/supabase-js";

/**
 * Supabase client — singleton inicializado a partir de variáveis de ambiente.
 *
 * Defina em frontend/.env.local (não commitado):
 *   VITE_SUPABASE_URL=https://<projeto>.supabase.co
 *   VITE_SUPABASE_ANON_KEY=eyJhbGciOi...
 *
 * Se ambos forem omitidos, isSupabaseEnabled() retorna false e o sistema
 * opera só com state local — sem persistência em nuvem.
 */

const URL_ENV  = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const KEY_ENV  = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

let _client: SupabaseClient | null = null;

export function isSupabaseEnabled(): boolean {
  return !!(URL_ENV && KEY_ENV);
}

export function getSupabase(): SupabaseClient | null {
  if (!isSupabaseEnabled()) return null;
  if (_client) return _client;
  _client = createClient(URL_ENV!, KEY_ENV!, {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      storageKey: "orgaudi-auth",
    },
  });
  return _client;
}

/** Types DB — espelham as tabelas do schema 0001_orgaudi_init.sql */
export interface DbEspolio {
  id: string;
  user_id: string;
  nome: string;
  cpf_falecido: string | null;
  data_obito: string | null;
  data_partilha: string | null;
  created_at: string;
  updated_at: string;
}

export interface DbHerdeiro {
  id: string;
  espolio_id: string;
  nome: string;
  cpf: string | null;
  fracao_monte: number | null;
  eh_meeiro: boolean;
  ordem: number;
}

export interface DbBem {
  id: string;
  espolio_id: string;
  identificacao: string;
  matricula: string | null;
  municipio: string | null;
  regime: string | null;
  opcao: string | null;
  eh_imovel: boolean;
  custo_aquisicao_dirpf: number | null;
  data_aquisicao: string | null;
  valor_partilha: number | null;
  valor_venda: number | null;
  data_operacao: string | null;
  ordem: number;
}
