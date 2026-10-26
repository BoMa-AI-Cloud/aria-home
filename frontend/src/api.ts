export type Availability =
  | "available"
  | "missing"
  | "stale"
  | "invalid"
  | "conflicting";

export type DataMode = "synthetic" | "replay" | "live";

export type SourceKind = "calendar" | "thermostat" | "electrical" | "weather";

export interface SourceStatus {
  source: SourceKind;
  availability: Availability;
  record_count: number;
  newest_observed_at: string | null;
  age_s: number | null;
  mode: DataMode;
  notes: string[];
  missing_count: number;
  stale_count: number;
}

export interface HealthResponse {
  status: string;
  service: string;
  data_mode: DataMode;
}

export interface SourcesResponse {
  data_mode: DataMode;
  at: string;
  sources: SourceStatus[];
}

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`GET ${path} failed with status ${response.status}`);
  }
  return (await response.json()) as T;
}

export function fetchHealth(): Promise<HealthResponse> {
  return fetchJson<HealthResponse>("/api/health");
}

export function fetchSources(at?: string): Promise<SourcesResponse> {
  const query = at ? `?at=${encodeURIComponent(at)}` : "";
  return fetchJson<SourcesResponse>(`/api/sources${query}`);
}
