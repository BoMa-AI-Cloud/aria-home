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

export type Readiness = "on_track" | "at_risk" | "cannot_tell";

export type InvestigationStatus = "ok" | "rejected" | "unavailable";

export interface InvestigationObservation {
  text: string;
  evidence_ids: string[];
}

export interface InvestigationHypothesis {
  text: string;
  supporting_ids: string[];
  conflicting_ids: string[];
}

export interface InvestigationFollowUp {
  observation: string;
  when: string;
}

export interface InvestigationOutput {
  observations: InvestigationObservation[];
  hypotheses: InvestigationHypothesis[];
  unknowns: string[];
  clarification: string;
  follow_up: InvestigationFollowUp;
  readiness: Readiness;
  limitations: string[];
}

export interface TargetGap {
  gap: number;
  unit: string;
  latest_value: number;
  latest_observed_at: string | null;
  target_temp: number;
  target_unit: string;
}

export interface InvestigationSummary {
  power_context_statement: string | null;
  continuity: string | null;
  metrics: {
    target_gap?: TargetGap | null;
    [key: string]: unknown;
  };
  power_context: {
    statement?: string;
    limitations?: string[];
    [key: string]: unknown;
  };
  [key: string]: unknown;
}

export interface InvestigationResponse {
  status: InvestigationStatus;
  output: InvestigationOutput | null;
  reasons: string[];
  model_id: string | null;
  prompt_version: string;
  provider_mode: string | null;
  summary: InvestigationSummary;
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

export function fetchInvestigation(at?: string): Promise<InvestigationResponse> {
  const query = at ? `?at=${encodeURIComponent(at)}` : "";
  return fetchJson<InvestigationResponse>(`/api/investigation${query}`);
}
