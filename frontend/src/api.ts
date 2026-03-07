export const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000/api";

export type GenerationStatus = "pending" | "generating" | "completed" | "failed";

export interface SearchBook {
  work_id: string;
  title: string;
  authors: string | null;
  first_publish_year: number | null;
  cover_url: string | null;
}

export interface SearchResponse {
  query: string;
  count: number;
  results: SearchBook[];
}

export interface Book {
  work_id: string;
  title: string;
  authors: string | null;
  description: string | null;
  cover_url: string | null;
  subjects: string[];
}

export interface GenerationMeta {
  work_id: string;
  status: GenerationStatus;
  section: "summary_llm" | "key_ideas" | "critique";
  error_message: string | null;
  model: string | null;
  tokens_prompt: number | null;
  tokens_completion: number | null;
  generation_time_ms: number | null;
  updated_at: string;
}

export interface KeyIdeasResponse extends GenerationMeta {
  section: "key_ideas";
  key_ideas: string | null;
}

export interface CritiqueResponse extends GenerationMeta {
  section: "critique";
  strengths: string | null;
  weaknesses: string | null;
  who_should_read: string | null;
}

export interface SummaryResponse extends GenerationMeta {
  section: "summary_llm";
  source: "openlibrary" | "llm";
  summary: string | null;
}

export interface SurpriseResponse {
  work_id: string;
  title?: string;
  authors?: string;
}

export interface ApiMeta {
  requestId: string | null;
}

export interface ApiResult<T> {
  data: T;
  meta: ApiMeta;
}

class ApiError extends Error {
  details: string;

  constructor(message: string, details: string) {
    super(message);
    this.details = details;
  }
}

function stringifyDetail(detail: unknown): string {
  if (!detail) {
    return "No additional details provided.";
  }
  if (typeof detail === "string") {
    return detail;
  }
  try {
    return JSON.stringify(detail, null, 2);
  } catch {
    return String(detail);
  }
}

async function fetchJson<T>(path: string): Promise<T> {
  const result = await fetchJsonWithMeta<T>(path);
  return result.data;
}

async function fetchJsonWithMeta<T>(path: string): Promise<ApiResult<T>> {
  const res = await fetch(`${API_BASE}${path}`);
  const text = await res.text();
  let payload: unknown = null;
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = text;
    }
  }

  if (!res.ok) {
    const detail =
      typeof payload === "object" && payload !== null && "detail" in payload
        ? (payload as { detail: unknown }).detail
        : payload;
    throw new ApiError(`API ${res.status} ${res.statusText}`, stringifyDetail(detail));
  }

  return {
    data: payload as T,
    meta: {
      requestId: res.headers.get("x-request-id"),
    },
  };
}

export function formatError(error: unknown): string {
  if (error instanceof ApiError) {
    return `${error.message}\n${error.details}`;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return String(error);
}

export const api = {
  search: (q: string) => fetchJson<SearchResponse>(`/search?q=${encodeURIComponent(q)}`),
  getBook: (workId: string) => fetchJson<Book>(`/books/${workId}`),
  getSummary: (workId: string, retry = false) =>
    fetchJson<SummaryResponse>(`/books/${workId}/summary${retry ? "?retry=true" : ""}`),
  getSummaryWithMeta: (workId: string, retry = false) =>
    fetchJsonWithMeta<SummaryResponse>(`/books/${workId}/summary${retry ? "?retry=true" : ""}`),
  getKeyIdeas: (workId: string, retry = false) =>
    fetchJson<KeyIdeasResponse>(`/books/${workId}/key-ideas${retry ? "?retry=true" : ""}`),
  getKeyIdeasWithMeta: (workId: string, retry = false) =>
    fetchJsonWithMeta<KeyIdeasResponse>(`/books/${workId}/key-ideas${retry ? "?retry=true" : ""}`),
  getCritique: (workId: string, retry = false) =>
    fetchJson<CritiqueResponse>(`/books/${workId}/critique${retry ? "?retry=true" : ""}`),
  getCritiqueWithMeta: (workId: string, retry = false) =>
    fetchJsonWithMeta<CritiqueResponse>(`/books/${workId}/critique${retry ? "?retry=true" : ""}`),
  surprise: () => fetchJson<SurpriseResponse>("/surprise"),
};
