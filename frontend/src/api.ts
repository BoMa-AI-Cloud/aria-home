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

export type OutcomeStatus =
  | "awaiting_measurement"
  | "warming_observed"
  | "target_reached"
  | "not_observed_by_deadline"
  | "unable_to_verify";

export interface OutcomeResult {
  status: OutcomeStatus;
  supporting_ids: string[];
  sample_count: number;
  first_value: number | null;
  last_value: number | null;
  note: string | null;
  evaluated_at: string;
}

export interface OutcomeHistoryEntry {
  investigation_id: string;
  evaluated_at: string;
  status: OutcomeStatus;
  sample_count: number;
  note: string | null;
}

export interface FollowUpPayload {
  investigation_id: string;
  created_at: string;
  deadline: string;
  target_temp: number;
  target_unit: string;
  [key: string]: unknown;
}

export interface CreateInvestigationResponse {
  data_mode: DataMode;
  investigation_id: string;
  scenario: string;
  status: InvestigationStatus;
  investigation: Record<string, unknown> | null;
  follow_up: FollowUpPayload | null;
  outcome: OutcomeResult;
}

export interface FollowUpResponse {
  data_mode: DataMode;
  investigation_id: string;
  scenario: string;
  status: OutcomeStatus;
  outcome: OutcomeResult;
  follow_up: FollowUpPayload | null;
  supporting_ids: string[];
  history: OutcomeHistoryEntry[];
}

export async function createInvestigation(
  scenario: string,
  at: string,
): Promise<CreateInvestigationResponse> {
  const query = `?scenario=${encodeURIComponent(scenario)}&at=${encodeURIComponent(at)}`;
  const response = await fetch(`/api/investigations${query}`, { method: "POST" });
  if (!response.ok) {
    throw new Error(`POST /api/investigations failed with status ${response.status}`);
  }
  return (await response.json()) as CreateInvestigationResponse;
}

export function fetchFollowUp(investigationId: string, at: string): Promise<FollowUpResponse> {
  return fetchJson<FollowUpResponse>(
    `/api/follow-ups/${encodeURIComponent(investigationId)}?at=${encodeURIComponent(at)}`,
  );
}
