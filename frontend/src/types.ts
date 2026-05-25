// Tipos espelhando o domínio Python (orgaudi_espolio).
// Mantenha em sincronia com src/orgaudi_espolio/dominio.py.

export const REGIMES = [
  "Transmissão a herdeiro (partilha)",
  "Venda pelo espólio a terceiro",
  "Cessão de direitos hereditários",
  "Fora do monte partilhável",
  "Indeterminado — requer classificação",
] as const;
export type Regime = (typeof REGIMES)[number];

export const OPCOES_ART23 = [
  "Valor histórico (§2º — sem IR; ganho diferido)",
  "Valor de mercado (§1º — IR no espólio agora)",
  "Não aplicável a este regime",
] as const;
export type OpcaoArt23 = (typeof OPCOES_ART23)[number];

export type StatusApuracao = "Conclusivo" | "Pendente — faltam dados ou classificação";

export interface Herdeiro {
  nome: string;
  cpf: string;
  fracao_monte: number;
  eh_meeiro: boolean;
}

export interface Bem {
  identificacao: string;
  matricula: string;
  municipio?: string;
  custo_aquisicao_dirpf: number | null;
  data_aquisicao: string | null;     // YYYY-MM-DD
  valor_partilha: number | null;
  valor_venda: number | null;
  regime: Regime;
  data_operacao: string | null;
  opcao: OpcaoArt23;
  eh_imovel: boolean;
}

export interface Espolio {
  nome: string;
  cpf_falecido: string;
  data_obito: string;        // YYYY-MM-DD
  data_partilha: string;
  herdeiros: Herdeiro[];
  bens: Bem[];
}

export interface ResultadoFR {
  aplicavel: boolean;
  motivo_inaplicavel: string;
  memoria: string[];
  m1: number;
  m2: number;
  fr1: number;
  fr2: number;
  reducao_7713: number;
  base_calculo_final: number;
}

export interface ResultadoBem {
  status: StatusApuracao | null;
  regime: string | null;
  ganho_bruto: number | null;
  ganho_diferido: number | null;
  base_tributavel: number | null;
  base_custo_herdeiro: number | null;
  ir_espolio: number | null;
  ir_herdeiros: Record<string, {
    fracao: number;
    ganho: number;
    base_tributavel: number;
    ir: number;
  }> | null;
  nota: string | null;
  alerta_reducao: string | null;
  fatores_reducao: ResultadoFR | null;
}

export interface BemApurado extends Bem {
  pendencias: string[];
  resultado: ResultadoBem;
}

export interface ResumoApuracao {
  espolio: string;
  ir_espolio_total: number;
  bens_conclusivos: number;
  bens_pendentes: number;
  conclusivo: boolean;
  soma_fracoes_herdeiros: number;
  audit_hash?: string;
}

export interface ApuracaoResponse {
  resumo: ResumoApuracao;
  bens: BemApurado[];
}

export interface BemExtraido {
  identificacao: string;
  matricula: string | null;
  municipio: string | null;
  custo_aquisicao_dirpf: number | null;
  data_aquisicao_iso: string | null;
  valor_partilha: number | null;
  valor_venda: number | null;
  data_operacao_iso: string | null;
  eh_imovel: boolean | null;
  regime_sugerido: string | null;
  opcao_art23_sugerida: string | null;
  confianca: string;
  rationale: string;
  fonte: string;
}

export interface HerdeiroExtraido {
  nome: string | null;
  cpf: string | null;
  fracao_monte: number | null;
  eh_meeiro: boolean | null;
  fonte: string;
}

export interface EspolioExtraido {
  nome_espolio: string | null;
  cpf_falecido: string | null;
  data_obito_iso: string | null;
  data_partilha_iso: string | null;
  herdeiros: HerdeiroExtraido[];
  bens: BemExtraido[];
  observacoes_globais: string[];
  documentos_analisados: string[];
}

export interface ExtracaoUso {
  input_tokens: number;
  output_tokens: number;
  cache_creation_input_tokens: number;
  cache_read_input_tokens: number;
  stop_reason: string;
}

export interface ExtracaoResponse {
  espolio: EspolioExtraido;
  uso: ExtracaoUso;
}

export interface VerificacaoIsencao {
  bem: string;
  isencao: string;
  base_legal: string;
  elegivel_em_tese: boolean;
  requisitos_a_confirmar: string[];
  observacao: string;
}

export interface RecomendacaoBem {
  bem: string;
  economia_vs_pior: number;
  recomendado: {
    descricao: string;
    base_legal: string;
    ir_espolio: number;
    ir_herdeiros_futuro_estimado: number;
    observacao: string;
  };
  cenarios: Array<{
    descricao: string;
    base_legal: string;
    ir_espolio: number;
    ir_herdeiros_futuro_estimado: number;
    observacao: string;
  }>;
  nota_decisao: string;
}
