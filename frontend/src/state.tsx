import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useReducer,
} from "react";
import type {
  ApuracaoResponse,
  Espolio,
  EspolioExtraido,
  RecomendacaoBem,
  VerificacaoIsencao,
} from "./types";
import { fetchExemplo } from "./api";

type Estado = {
  espolio: Espolio | null;
  activeEspolioId: string | null;
  authModalOpen: boolean;
  abrirModalOpen: boolean;
  apuracao: ApuracaoResponse | null;
  relatorio: string | null;
  recomendacoes: RecomendacaoBem[] | null;
  isencoes: VerificacaoIsencao[] | null;
  extracao: EspolioExtraido | null;
  analise: string | null;
  apiKey: string | null;
};

type Acao =
  | { type: "SET_ESPOLIO"; espolio: Espolio; id?: string | null }
  | { type: "SET_ACTIVE_ID"; id: string | null }
  | { type: "SET_AUTH_MODAL_OPEN"; open: boolean }
  | { type: "SET_ABRIR_MODAL_OPEN"; open: boolean }
  | { type: "PATCH_ESPOLIO"; patch: Partial<Espolio> }
  | { type: "SET_APURACAO"; apuracao: ApuracaoResponse | null }
  | { type: "SET_RELATORIO"; texto: string | null }
  | { type: "SET_RECOMENDACOES"; r: RecomendacaoBem[] | null }
  | { type: "SET_ISENCOES"; i: VerificacaoIsencao[] | null }
  | { type: "SET_EXTRACAO"; e: EspolioExtraido | null }
  | { type: "SET_ANALISE"; texto: string | null }
  | { type: "APPEND_ANALISE"; chunk: string }
  | { type: "SET_API_KEY"; key: string | null };

const initialState: Estado = {
  espolio: null,
  activeEspolioId: null,
  authModalOpen: false,
  abrirModalOpen: false,
  apuracao: null,
  relatorio: null,
  recomendacoes: null,
  isencoes: null,
  extracao: null,
  analise: null,
  apiKey: null,
};

function reducer(s: Estado, a: Acao): Estado {
  switch (a.type) {
    case "SET_ESPOLIO":
      // Mudar o espólio invalida resultados derivados
      return {
        ...s,
        espolio: a.espolio,
        activeEspolioId: a.id !== undefined ? a.id : null,
        apuracao: null, relatorio: null,
        recomendacoes: null, isencoes: null, analise: null,
      };
    case "SET_ACTIVE_ID":
      return { ...s, activeEspolioId: a.id };
    case "SET_AUTH_MODAL_OPEN":
      return { ...s, authModalOpen: a.open };
    case "SET_ABRIR_MODAL_OPEN":
      return { ...s, abrirModalOpen: a.open };
    case "PATCH_ESPOLIO":
      if (!s.espolio) return s;
      return {
        ...s,
        espolio: { ...s.espolio, ...a.patch },
        apuracao: null, relatorio: null,
        recomendacoes: null, isencoes: null, analise: null,
      };
    case "SET_APURACAO":    return { ...s, apuracao: a.apuracao };
    case "SET_RELATORIO":   return { ...s, relatorio: a.texto };
    case "SET_RECOMENDACOES": return { ...s, recomendacoes: a.r };
    case "SET_ISENCOES":    return { ...s, isencoes: a.i };
    case "SET_EXTRACAO":    return { ...s, extracao: a.e };
    case "SET_ANALISE":     return { ...s, analise: a.texto };
    case "APPEND_ANALISE":
      return { ...s, analise: (s.analise || "") + a.chunk };
    case "SET_API_KEY":     return { ...s, apiKey: a.key };
  }
}

type Ctx = {
  state: Estado;
  setEspolio: (e: Espolio, id?: string | null) => void;
  setActiveEspolioId: (id: string | null) => void;
  setAuthModalOpen: (open: boolean) => void;
  setAbrirModalOpen: (open: boolean) => void;
  patchEspolio: (patch: Partial<Espolio>) => void;
  setApuracao: (a: ApuracaoResponse | null) => void;
  setRelatorio: (t: string | null) => void;
  setRecomendacoes: (r: RecomendacaoBem[] | null) => void;
  setIsencoes: (i: VerificacaoIsencao[] | null) => void;
  setExtracao: (e: EspolioExtraido | null) => void;
  setAnalise: (t: string | null) => void;
  appendAnalise: (c: string) => void;
  setApiKey: (k: string | null) => void;
  reset: () => Promise<void>;
  novo: () => void;
};

const C = createContext<Ctx | null>(null);

export function StateProvider(props: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState, (init) => {
    // hidrata API key do localStorage se houver
    if (typeof window !== "undefined") {
      const k = window.localStorage.getItem("anthropic_api_key");
      if (k) return { ...init, apiKey: k };
    }
    return init;
  });

  // carrega exemplo no primeiro mount
  useEffect(() => {
    if (state.espolio) return;
    fetchExemplo()
      .then((e) => dispatch({ type: "SET_ESPOLIO", espolio: e }))
      .catch(() => {
        /* backend offline — UI exibe estado vazio */
      });
  }, [state.espolio]);

  const setApiKey = useCallback((k: string | null) => {
    dispatch({ type: "SET_API_KEY", key: k });
    if (typeof window !== "undefined") {
      if (k) window.localStorage.setItem("anthropic_api_key", k);
      else window.localStorage.removeItem("anthropic_api_key");
    }
  }, []);

  const reset = useCallback(async () => {
    const e = await fetchExemplo();
    dispatch({ type: "SET_ESPOLIO", espolio: e });
    dispatch({ type: "SET_EXTRACAO", e: null });
  }, []);

  const novo = useCallback(() => {
    const hoje = new Date().toISOString().slice(0, 10);
    dispatch({
      type: "SET_ESPOLIO", espolio: {
        nome: "",
        cpf_falecido: "",
        data_obito: hoje,
        data_partilha: hoje,
        herdeiros: [],
        bens: [],
      }
    });
    dispatch({ type: "SET_EXTRACAO", e: null });
  }, []);

  const value = useMemo<Ctx>(() => ({
    state,
    setEspolio: (e, id) => dispatch({ type: "SET_ESPOLIO", espolio: e, id }),
    setActiveEspolioId: (id) => dispatch({ type: "SET_ACTIVE_ID", id }),
    setAuthModalOpen: (open) => dispatch({ type: "SET_AUTH_MODAL_OPEN", open }),
    setAbrirModalOpen: (open) => dispatch({ type: "SET_ABRIR_MODAL_OPEN", open }),
    patchEspolio: (p) => dispatch({ type: "PATCH_ESPOLIO", patch: p }),
    setApuracao: (a) => dispatch({ type: "SET_APURACAO", apuracao: a }),
    setRelatorio: (t) => dispatch({ type: "SET_RELATORIO", texto: t }),
    setRecomendacoes: (r) =>
      dispatch({ type: "SET_RECOMENDACOES", r }),
    setIsencoes: (i) => dispatch({ type: "SET_ISENCOES", i }),
    setExtracao: (e) => dispatch({ type: "SET_EXTRACAO", e }),
    setAnalise: (t) => dispatch({ type: "SET_ANALISE", texto: t }),
    appendAnalise: (c) => dispatch({ type: "APPEND_ANALISE", chunk: c }),
    setApiKey,
    reset,
    novo,
  }), [state, setApiKey, reset, novo]);

  return <C.Provider value={value}>{props.children}</C.Provider>;
}

export function useEspolio(): Ctx {
  const v = useContext(C);
  if (!v) throw new Error("useEspolio must be used inside StateProvider");
  return v;
}
