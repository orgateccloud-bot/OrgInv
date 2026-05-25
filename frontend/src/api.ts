import type {
  ApuracaoResponse,
  Espolio,
  ExtracaoResponse,
  RecomendacaoBem,
  VerificacaoIsencao,
} from "./types";

// Vite proxy encaminha /api → http://localhost:8000
const BASE = "";

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(BASE + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    let msg = `HTTP ${r.status}`;
    try {
      const j = await r.json();
      msg = j.detail || msg;
    } catch {
      /* ignore */
    }
    throw new Error(msg);
  }
  return r.json() as Promise<T>;
}

export async function health() {
  const r = await fetch("/api/health");
  return r.json() as Promise<{
    status: string;
    version: string;
    anthropic_key_set: boolean;
  }>;
}

export async function fetchExemplo(): Promise<Espolio> {
  const r = await fetch("/api/exemplo");
  return r.json();
}

export const apurar = (espolio: Espolio) =>
  postJson<ApuracaoResponse>("/api/apurar", espolio);

export const relatorio = (espolio: Espolio) =>
  postJson<{ texto: string }>("/api/relatorio", espolio);

export const otimizar = (espolio: Espolio) =>
  postJson<RecomendacaoBem[]>("/api/otimizar", espolio);

export const isencoes = (espolio: Espolio) =>
  postJson<VerificacaoIsencao[]>("/api/isencoes", espolio);

export async function laudoXlsx(espolio: Espolio): Promise<Blob> {
  const r = await fetch("/api/laudo/xlsx", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(espolio),
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.blob();
}

export async function laudoPdf(
  espolio: Espolio,
  analiseIa: string | null,
): Promise<Blob> {
  const r = await fetch("/api/laudo/pdf", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ espolio, analise_ia: analiseIa }),
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.blob();
}

export async function laudoReactive(espolio: Espolio): Promise<Blob> {
  const r = await fetch("/api/laudo/reactive", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(espolio),
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.blob();
}


export async function extrairPdfs(
  arquivos: File[],
  instrucaoExtra: string,
  apiKey: string | null,
): Promise<ExtracaoResponse> {
  const fd = new FormData();
  for (const f of arquivos) fd.append("files", f, f.name);
  fd.append("instrucao_extra", instrucaoExtra);
  if (apiKey) fd.append("api_key", apiKey);
  const r = await fetch("/api/ia/extrair", { method: "POST", body: fd });
  if (!r.ok) {
    let msg = `HTTP ${r.status}`;
    try {
      const j = await r.json();
      msg = j.detail || msg;
    } catch {
      /* ignore */
    }
    throw new Error(msg);
  }
  return r.json();
}

function anonymizeEspolio(esp: Espolio): Espolio {
  return {
    ...esp,
    nome: esp.nome ? "Falecido(a)" : "",
    cpf_falecido: esp.cpf_falecido ? "000.000.000-00" : "",
    herdeiros: esp.herdeiros.map((h, i) => ({
      ...h,
      nome: h.nome ? `Herdeiro ${i + 1}` : "",
      cpf: h.cpf ? "000.000.000-00" : "",
    })),
  };
}

/**
 * Streaming de análise via fetch + ReadableStream + parsing SSE manual.
 * (EventSource não suporta POST.) Chama onChunk para cada token.
 */
export async function analisarStream(
  espolio: Espolio,
  apiKey: string | null,
  onChunk: (texto: string) => void,
  signal?: AbortSignal,
): Promise<void> {
  const r = await fetch("/api/ia/analisar", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ espolio: anonymizeEspolio(espolio), api_key: apiKey }),
    signal,
  });
  if (!r.ok || !r.body) {
    let msg = `HTTP ${r.status}`;
    try {
      const j = await r.json();
      msg = j.detail || msg;
    } catch {
      /* ignore */
    }
    throw new Error(msg);
  }

  const reader = r.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let i: number;
    while ((i = buffer.indexOf("\n\n")) !== -1) {
      const raw = buffer.slice(0, i);
      buffer = buffer.slice(i + 2);
      // Cada evento SSE pode ter linhas "event: X" e "data: Y".
      let event = "message";
      let data = "";
      for (const line of raw.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) data += line.slice(5).trim();
      }
      if (event === "done") return;
      if (event === "error") {
        try {
          const j = JSON.parse(data);
          throw new Error(j.message || "Erro no stream");
        } catch (e) {
          if (e instanceof Error && e.message) throw e;
          throw new Error("Erro no stream");
        }
      }
      if (event === "message" && data) {
        try {
          const j = JSON.parse(data) as { t: string };
          onChunk(j.t);
        } catch {
          /* ignore malformed chunks */
        }
      }
    }
  }
}
