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

export type ReadinessStatus = "on_track" | "at_risk" | "cannot_tell" | "arrival_passed";

export type Readiness = ReadinessStatus;

export type InvestigationStatus = "ok" | "rejected" | "unavailable";

export interface ContextFlags {
  trip_cancelled: boolean;
  trip_unconfirmed: boolean;
  trip_mismatched: boolean;
  confirmation_outdated: boolean;
}

export interface ReadinessThresholds {
  MIN_SAMPLES: number;
  MIN_COVERAGE: number;
  STALE_READING_AGE_S: number;
  SMALL_GAP_F: number;
  MIN_TREND_WINDOW_S: number;
  MIN_RISE_F: number;
  MIN_RATE_PER_HOUR_F: number;
  PROJECTION_MARGIN_F: number;
  ARRIVAL_TIME_MARGIN_S: number;
}

export interface ReadinessInputs {
  gap: number | null;
  gap_f: number | null;
  unit: string | null;
  last_value: number | null;
  target_temp: number | null;
  rate_per_hour: number | null;
  rate_per_hour_f: number | null;
  change: number | null;
  change_f: number | null;
  sample_count: number;
  coverage: number | null;
  first_observed_at: string | null;
  last_observed_at: string | null;
  trend_window_s: number | null;
  planned_arrival: string | null;
  now: string | null;
  hours_to_arrival: number | null;
  thermostat_availability: Availability | null;
  flags: ContextFlags;
  thresholds: ReadinessThresholds;
  reading_age_s?: number;
  projected_value_at_arrival_f?: number;
  target_temp_f?: number;
  hours_to_close_gap?: number | null;
}

export interface ReadinessResult {
  status: ReadinessStatus;
  reasons: string[];
  inputs: ReadinessInputs;
}

export interface IndoorTrend {
  zone: string;
  sample_count: number;
  missing_count: number;
  coverage: number;
  coverage_basis: string;
  gaps_over_cadence: number;
  largest_gap_s: number | null;
  first_value: number | null;
  first_observed_at: string | null;
  last_value: number | null;
  last_observed_at: string | null;
  change: number | null;
  rate_per_hour: number | null;
  unit: string;
  unit_converted: boolean;
  sufficient: boolean;
}

export interface TargetGap {
  gap: number;
  unit: string;
  latest_value: number;
  latest_observed_at: string | null;
  target_temp: number;
  target_unit: string;
}

export interface CircuitActivity {
  circuit_id: string;
  sample_count: number;
  missing_count: number;
  coverage: number;
  coverage_basis: string;
  gaps_over_cadence: number;
  largest_gap_s: number | null;
  max_w: number | null;
  mean_w: number | null;
  active: boolean;
  binding: string;
  noise_floor_w: number;
  unit: string;
  first_observed_at: string | null;
  last_observed_at: string | null;
  meaning: string;
}

export interface Trip {
  id: string;
  property_id: string;
  title: string;
  planned_arrival: string;
  revision: number;
  cancelled: boolean;
  known_at: string | null;
  revision_id: string | null;
  target_temp: number | null;
  target_unit: string | null;
}

export interface HomeownerConfirmation {
  trip_id: string;
  property_id: string;
  target_temp: number;
  target_unit: string;
  notify_homeowner: boolean;
  manager_authorized: boolean;
  confirmed_at: string;
  revision_id: string | null;
  trip_revision: number | null;
  trip_revision_id: string | null;
}

export interface MetricsResponse {
  data_mode: DataMode;
  scenario?: string;
  timezone?: string;
  computed_by: string;
  at: string;
  zone: string;
  window: { start: string; end: string };
  indoor_trend: IndoorTrend;
  target_gap: TargetGap | null;
  circuits: Record<string, CircuitActivity>;
  trip: Trip | null;
  confirmation: HomeownerConfirmation | null;
  readiness_flags: ContextFlags;
  flags: ContextFlags;
  context_flags: ContextFlags;
  readiness: ReadinessResult;
  computed_readiness: ReadinessStatus;
}

export interface CircuitContext {
  circuit_id: string;
  binding: "confirmed" | "candidate" | "unknown";
  status: "fresh_active" | "fresh_quiet" | "stale" | "missing" | "invalid" | "conflicting";
  age_s: number | null;
  last_value: number | null;
  last_observed_at: string | null;
}

export interface PowerLineage {
  meter_ids: string[];
  lineage_count: number;
  counts_by_status: Record<string, number>;
  coverage: number;
  largest_gap_s: number | null;
}

export interface PowerContext {
  per_circuit: CircuitContext[];
  lineage: PowerLineage;
  mains: "not_available" | "measured_fresh" | "measured_stale" | "calculated_only";
  heating_binding: "confirmed" | "candidate_only" | "unknown";
  backup: "known_none" | "known_present" | "unknown";
  continuity:
    | "activity_weighs_against_total_loss"
    | "visibility_lost"
    | "insufficient_evidence"
    | "conflicting_evidence";
  statement: string;
  limitations: string[];
  window_start: string;
  now: string;
}

export interface InvestigationMetrics {
  zone: string;
  indoor_trend: IndoorTrend;
  target_gap: TargetGap | null;
  circuits: Record<string, CircuitActivity>;
}

export interface InvestigationSummary {
  source_statuses: SourceStatus[];
  metrics: InvestigationMetrics;
  power_context: PowerContext;
  power_context_statement: string | null;
  continuity: string | null;
  readiness: ReadinessResult;
  computed_readiness: ReadinessStatus | null;
}

export type ClaimType =
  | "current_temperature"
  | "target_temperature"
  | "target_gap"
  | "electrical_activity"
  | "equipment_function";

export interface InvestigationFact {
  claim_type: ClaimType;
  evidence_id: string;
  field: string;
  value: number | string | boolean;
  unit: string | null;
  at: string | null;
}

export interface InvestigationHypothesis {
  text: string;
  supporting_ids: string[];
  conflicting_ids: string[];
}

export interface InvestigationFollowUp {
  observation: string;
  when: string | null;
  next_check_at: string | null;
  schedule_status: string;
  deadline_passed: boolean;
}

export interface InvestigationOutput {
  facts: InvestigationFact[];
  verified_facts: string[];
  interpretation: string;
  hypotheses: InvestigationHypothesis[];
  unknowns: string[];
  clarification: string;
  follow_up: InvestigationFollowUp;
  readiness: ReadinessStatus;
  limitations: string[];
}

export interface EvidencePackTrip {
  id: string;
  property_id: string;
  planned_arrival: string;
  revision: number;
  revision_id: string | null;
  known_at: string | null;
  cancelled: boolean;
  title: { untrusted_text: string; quoted: string };
}

export interface EvidenceItem {
  id: string;
  source?: SourceKind;
  kind?: string;
  subject?: string;
  quantity?: string;
  value?: number | string | null;
  unit?: string | null;
  observed_at?: string;
  received_at?: string;
  type?: string;
  name?: string;
  circuit_id?: string;
  data?: Record<string, unknown>;
}

export interface EvidencePack {
  prompt_version: string;
  at: string;
  window: { start: string; end: string };
  data_mode: DataMode;
  trip: EvidencePackTrip | null;
  confirmation: HomeownerConfirmation | null;
  readiness_flags: ContextFlags;
  flags: ContextFlags;
  context_flags: ContextFlags;
  as_of: {
    at: string;
    flags: ContextFlags;
    trip_revision_id: string | null;
    confirmation_visible: boolean;
  };
  source_statuses: SourceStatus[];
  metrics: InvestigationMetrics;
  power_context: PowerContext;
  evidence: EvidenceItem[];
  evidence_ids: string[];
  readiness: ReadinessResult;
  computed_readiness: ReadinessStatus;
}

export interface Investigation {
  status: InvestigationStatus;
  output: InvestigationOutput | null;
  reasons: string[];
  model_id: string | null;
  prompt_version: string;
  provider_mode: string | null;
  latency_ms: number | null;
  input_tokens: number | null;
  output_tokens: number | null;
  token_usage: { input_tokens: number | null; output_tokens: number | null };
  max_tokens_used: number | null;
  summary: InvestigationSummary;
  evidence_pack: EvidencePack;
}

export interface InvestigationResponse extends Omit<Investigation, "status"> {
  status: InvestigationStatus | "pending" | "recovery_required";
  inference_state?: string;
  data_mode: DataMode;
  scenario?: string;
  at?: string;
  timezone?: string;
  readiness: ReadinessResult | null;
  computed_readiness: ReadinessStatus | null;
  evaluated_at?: string;
}

export interface CreatedInvestigation extends Investigation {
  id: string;
  investigation_id: string;
  scenario: string;
  evaluated_at: string;
  readiness: ReadinessResult | null;
  computed_readiness: ReadinessStatus | null;
}

export interface FollowUpSchedule {
  status: string;
  schedule_status: string;
  flag: string | null;
  flags: string[];
  deadline_passed: boolean;
  evaluated_at: string;
  deadline: string | null;
  arrival: string | null;
  earliest: string;
  latest: string;
  cadence_s: number;
  next_check_at: string | null;
  scheduled_at: string | null;
  when: string | null;
  computed_next_check_at: string | null;
  model_when: string | null;
  model_time_valid: boolean;
  model_time_rejected: boolean;
  model_time_reasons: string[];
}

export type NotificationAudience = "homeowner" | "property_manager" | "hvac_company";

export type NotificationState = "queued" | "simulated_delivered" | "refused" | string;

export interface NotificationAck {
  id: string;
  notification_id: string;
  actor: string;
  acknowledged_at: string;
  by: string;
  at: string;
}

export interface NotificationWhatsapp {
  state: string;
  message_id: string | null;
  attempted_at: string;
}

export interface Notification {
  id: string;
  investigation_id: string;
  audience: NotificationAudience;
  kind: string;
  idempotency_key: string;
  payload: Record<string, unknown>;
  created_at: string;
  delivery: string;
  state: NotificationState;
  refusal_reason: string | null;
  reason: string | null;
  acks: NotificationAck[];
  whatsapp?: NotificationWhatsapp | null;
}

export interface NotificationsResponse {
  data_mode: DataMode;
  scenario?: string;
  at?: string;
  timezone?: string;
  investigation_id: string | null;
  notifications: Notification[];
}

export interface AckNotificationResponse {
  data_mode: DataMode;
  message: string;
  acknowledgement: string;
  notification: Notification;
  ack: NotificationAck;
  acks: NotificationAck[];
}

export interface HealthResponse {
  status: string;
  service: string;
  data_mode: DataMode;
  scenario: string;
  at: string;
  timezone: string;
}

export interface SourcesResponse {
  data_mode: DataMode;
  scenario: string;
  at: string;
  timezone: string;
  sources: SourceStatus[];
}

export interface ArrivalAllowance {
  kind: string;
  minutes: number;
  label: string;
}

export interface ArrivalPlan {
  label?: string;
  landing?: string;
  airport_exit_baggage_allowance_min?: number;
  airport_exit_baggage_label?: string;
  driving_allowance_min?: number;
  driving_label?: string;
  planned_property_arrival?: string;
  derivation?: string;
}

export interface ContextResponse {
  data_mode: DataMode;
  scenario: string;
  at: string;
  timezone: string;
  confirmed: boolean;
  reason: string | null;
  reason_in_words?: string;
  property_label?: string;
  property_id?: string;
  planned_arrival?: string | null;
  arrival_plan?: ArrivalPlan | null;
  landing?: string | null;
  allowances?: ArrivalAllowance[];
  arrival_allowances?: ArrivalAllowance[];
  arrival_estimates_note?: string;
  target_temp?: number;
  target_unit?: string;
  target_temperature?: string;
  notify_homeowner?: boolean;
  homeowner_notification_preference?: boolean;
  manager_authorized?: boolean;
  manager_coordination_permission?: boolean;
  manager_coordination?: string;
  confirmed_at?: string | null;
  revision_id?: string | null;
  trip_revision_id?: string | null;
  trip?: Trip | null;
  confirmation?: HomeownerConfirmation | null;
  flags: ContextFlags;
  context_flags: ContextFlags;
  readiness_flags: ContextFlags;
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

export function fetchSources(scenario?: string, at?: string): Promise<SourcesResponse> {
  const params = new URLSearchParams();
  if (scenario) params.set("scenario", scenario);
  if (at) params.set("at", at);
  const query = params.toString() ? `?${params.toString()}` : "";
  return fetchJson<SourcesResponse>(`/api/sources${query}`);
}

export function fetchContext(scenario?: string, at?: string): Promise<ContextResponse> {
  const params = new URLSearchParams();
  if (scenario) params.set("scenario", scenario);
  if (at) params.set("at", at);
  const query = params.toString() ? `?${params.toString()}` : "";
  return fetchJson<ContextResponse>(`/api/context${query}`);
}

export function fetchMetrics(at?: string, scenario?: string): Promise<MetricsResponse> {
  const params = new URLSearchParams();
  if (at) params.set("at", at);
  if (scenario) params.set("scenario", scenario);
  const query = params.toString() ? `?${params.toString()}` : "";
  return fetchJson<MetricsResponse>(`/api/metrics${query}`);
}

export async function fetchInvestigation(at?: string, scenario?: string): Promise<InvestigationResponse> {
  const params = new URLSearchParams();
  if (at) params.set("at", at);
  if (scenario) params.set("scenario", scenario);
  const query = params.toString() ? `?${params.toString()}` : "";
  const path = `/api/investigation${query}`;
  const response = await fetch(path);
  if (response.status !== 200 && response.status !== 202 && response.status !== 409) {
    throw new Error(`GET ${path} failed with status ${response.status}`);
  }
  return (await response.json()) as InvestigationResponse;
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

export interface FollowUpTarget {
  target_temp: number;
  target_unit: string;
  min_samples: number;
  min_rise_f: number;
  zone: string;
  cadence_s: number | null;
}

export interface FollowUpPayload {
  investigation_id: string;
  created_at: string;
  target_temp: number;
  target_unit: string;
  deadline: string;
  min_samples: number;
  min_rise_f: number;
  zone: string;
  next_check_at: string | null;
  schedule_status: string;
  deadline_passed: boolean;
  cadence_s: number | null;
  target: FollowUpTarget | null;
  last_status: OutcomeStatus | null;
  status: OutcomeStatus | null;
  last_evaluated_at: string | null;
  supporting_ids: string[];
  when: string | null;
}

export type CreateInvestigationStatus =
  | InvestigationStatus
  | "deadline_passed"
  | "cannot_tell";

export interface CreateInvestigationResponse {
  data_mode: DataMode;
  at?: string;
  timezone?: string;
  investigation_id: string;
  id: string;
  scenario: string;
  status: CreateInvestigationStatus;
  investigation_status?: InvestigationStatus;
  readiness: ReadinessResult | null;
  computed_readiness: ReadinessStatus | null;
  investigation: CreatedInvestigation;
  follow_up: FollowUpPayload | null;
  follow_up_schedule: FollowUpSchedule;
  schedule: FollowUpSchedule;
  schedule_status: string;
  flag?: string | null;
  flags?: ContextFlags;
  readiness_flags?: ContextFlags;
  context_flags?: ContextFlags;
  deadline_passed: boolean;
  next_check_at: string | null;
  outcome: OutcomeResult | null;
  notifications?: Notification[];
  error?: string;
}

export type VerificationStage =
  | "telemetry_missing"
  | "reporting_restored"
  | "warming_observed"
  | "goal_verified"
  | "goal_not_maintained"
  | "arrival_met"
  | "unable_to_verify";

export interface VerificationResult {
  stage: VerificationStage;
  reasons: string[];
  supporting_ids: string[];
  corroboration_ids: string[];
  corroboration: string[];
  evaluated_at: string;
  goal_verified_at?: string | null;
  arrival_met_at?: string | null;
  latest_reading_used?: { id?: string | null; observed_at: string; received_at: string } | null;
}

export interface VerificationHistoryEntry {
  evaluated_at: string;
  stage: VerificationStage;
  sample_count: number | null;
}

export interface ScenarioEvent {
  id: string;
  kind: string;
  event_time: string;
  available_at: string;
  simulated: boolean;
  payload: Record<string, unknown>;
}

export interface EventsResponse {
  data_mode: DataMode;
  scenario: string;
  at: string;
  timezone?: string;
  events: ScenarioEvent[];
}

export type EvidenceTimelineKind =
  | "reporting_restored"
  | "warming_observed"
  | "target_reached"
  | "goal_verified"
  | "hvac_completion_report"
  | "arrival_checked";

export interface EvidenceTimelineEntry {
  kind: EvidenceTimelineKind;
  label: string;
  supporting_ids: string[];
  supporting_record_ids: string[];
  observed_at: string;
  received_at: string;
  available_at: string;
  first_known_at: string;
  evaluated_at: string;
  corroboration_only: boolean;
}

export interface FollowUpResponse {
  data_mode: DataMode;
  investigation_id: string;
  scenario: string;
  at?: string;
  timezone?: string;
  status: OutcomeStatus;
  outcome: OutcomeResult;
  follow_up: FollowUpPayload | null;
  supporting_ids: string[];
  history: OutcomeHistoryEntry[];
  verification?: VerificationResult | null;
  verification_history?: VerificationHistoryEntry[];
  evidence_timeline?: EvidenceTimelineEntry[];
  notifications?: Notification[];
}

export class RecoveryRequiredError extends Error {
  body: unknown;
  constructor(body: unknown) {
    super("POST /api/investigations requires explicit recovery (retry=true)");
    this.name = "RecoveryRequiredError";
    this.body = body;
  }
}

export interface CreateInvestigationOptions {
  signal?: AbortSignal;
  onPending?: (attempt: number, elapsedMs: number) => void;
  queryExtra?: string;
  deadlineMs?: number;
}

export const INFERENCE_LEASE_S = 120;
export const INFERENCE_POLL_MARGIN_S = 15;
export const INFERENCE_POLL_DEADLINE_MS =
  (INFERENCE_LEASE_S + INFERENCE_POLL_MARGIN_S) * 1000;

function sleepAbortable(ms: number, signal?: AbortSignal): Promise<void> {
  if (ms <= 0) return Promise.resolve();
  if (signal?.aborted) return Promise.reject(signal.reason ?? new DOMException("Aborted", "AbortError"));
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      signal?.removeEventListener("abort", onAbort);
      resolve();
    }, ms);
    const onAbort = () => {
      clearTimeout(timer);
      reject(signal?.reason ?? new DOMException("Aborted", "AbortError"));
    };
    signal?.addEventListener("abort", onAbort, { once: true });
  });
}

export async function createInvestigation(
  scenario: string,
  at: string,
  options?: CreateInvestigationOptions,
): Promise<CreateInvestigationResponse> {
  const extra = options?.queryExtra ? `&${options.queryExtra.replace(/^[?&]/, "")}` : "";
  const query = `?scenario=${encodeURIComponent(scenario)}&at=${encodeURIComponent(at)}${extra}`;
  const deadlineMs = options?.deadlineMs ?? INFERENCE_POLL_DEADLINE_MS;
  const start = Date.now();
  let attempt = 0;
  for (;;) {
    if (options?.signal?.aborted) {
      throw options.signal.reason ?? new DOMException("Aborted", "AbortError");
    }
    const response = await fetch(`/api/investigations${query}`, {
      method: "POST",
    });
    if (response.status === 202) {
      const body = (await response.json()) as { status?: string };
      if (body.status !== "pending") return body as CreateInvestigationResponse;
      const elapsed = Date.now() - start;
      options?.onPending?.(attempt, elapsed);
      const backoff = Math.min(200 * 2 ** attempt, 2000);
      if (elapsed + backoff > deadlineMs) {
        throw new Error("POST /api/investigations still pending");
      }
      await sleepAbortable(backoff, options?.signal);
      attempt += 1;
      continue;
    }
    if (response.status === 409) {
      const body = (await response.json().catch(() => null)) as {
        status?: string;
      } | null;
      if (body?.status === "recovery_required") {
        throw new RecoveryRequiredError(body);
      }
      throw new Error(`POST /api/investigations failed with status ${response.status}`);
    }
    if (!response.ok) {
      throw new Error(`POST /api/investigations failed with status ${response.status}`);
    }
    return (await response.json()) as CreateInvestigationResponse;
  }
}

export function fetchFollowUp(investigationId: string, at: string): Promise<FollowUpResponse> {
  return fetchJson<FollowUpResponse>(
    `/api/follow-ups/${encodeURIComponent(investigationId)}?at=${encodeURIComponent(at)}`,
  );
}

export function fetchEvents(scenario: string, at: string): Promise<EventsResponse> {
  const query = `?scenario=${encodeURIComponent(scenario)}&at=${encodeURIComponent(at)}`;
  return fetchJson<EventsResponse>(`/api/events${query}`);
}

export function fetchNotifications(investigationId?: string | null, at?: string): Promise<NotificationsResponse> {
  const params = new URLSearchParams();
  if (investigationId) params.set("investigation_id", investigationId);
  if (at) params.set("at", at);
  const query = params.toString() ? `?${params.toString()}` : "";
  return fetchJson<NotificationsResponse>(`/api/notifications${query}`);
}

export async function ackNotification(
  notificationId: string,
  actor: string,
  at?: string,
): Promise<AckNotificationResponse> {
  const response = await fetch(`/api/notifications/${encodeURIComponent(notificationId)}/ack`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(at ? { actor, at } : { actor }),
  });
  if (!response.ok) {
    throw new Error(`POST /api/notifications/${notificationId}/ack failed with status ${response.status}`);
  }
  return (await response.json()) as AckNotificationResponse;
}

export interface WhatsappStatusResponse {
  data_mode: DataMode;
  scenario?: string;
  at?: string;
  timezone?: string;
  configured: boolean;
}

export interface WhatsappSendResponse {
  data_mode: DataMode;
  scenario?: string;
  at?: string;
  timezone?: string;
  notification: Notification;
  whatsapp: NotificationWhatsapp | null;
  delivery: { attempted: boolean; reason?: string; state?: string; message_id?: string | null };
}

export async function fetchWhatsappStatus(): Promise<WhatsappStatusResponse | null> {
  try {
    const response = await fetch("/api/whatsapp/status");
    if (!response.ok) return null;
    return (await response.json()) as WhatsappStatusResponse;
  } catch {
    return null;
  }
}

export async function sendHvacWhatsapp(
  notificationId: string,
  at?: string,
): Promise<WhatsappSendResponse> {
  const query = at ? `?at=${encodeURIComponent(at)}` : "";
  const response = await fetch(`/api/notifications/${encodeURIComponent(notificationId)}/whatsapp${query}`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(`POST /api/notifications/${notificationId}/whatsapp failed with status ${response.status}`);
  }
  return (await response.json()) as WhatsappSendResponse;
}

export interface LivePowerCircuit {
  circuit: string;
  watts: number;
}

export interface LivePowerResponse {
  status: "ok" | "not_configured" | "unavailable";
  source: string;
  fetched_at: string | null;
  circuits: LivePowerCircuit[];
  cached?: boolean;
  error?: string;
}

export async function fetchLivePower(): Promise<LivePowerResponse | null> {
  try {
    const response = await fetch("/api/live-power");
    if (!response.ok) return null;
    return (await response.json()) as LivePowerResponse;
  } catch {
    return null;
  }
}
