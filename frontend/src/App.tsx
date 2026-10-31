import { Component, useEffect, useRef, useState, type ReactNode } from "react";
import {
  ackNotification,
  decideCaregiverPermission,
  createInvestigation,
  fetchContext,
  fetchCorrections,
  fetchEvents,
  fetchFollowUp,
  fetchHealth,
  fetchInvestigation,
  fetchLaws,
  fetchLivePower,
  fetchCameraConfigured,
  takeCameraSnapshot,
  fetchNotifications,
  fetchScenarios,
  fetchSources,
  fetchTrace,
  fetchVisual,
  fetchWatcher,
  fetchWhatsappStatus,
  resetPublicSession,
  RecoveryRequiredError,
  sendHvacWhatsapp,
  type Availability,
  type CameraSnapshotResponse,
  type CaregiverPermission,
  type ContextFlags,
  type ContextResponse,
  type CorrectionRecord,
  type CorrectionsResponse,
  type CreateInvestigationResponse,
  type EvidenceTimelineEntry,
  type HumanReportPayload,
  type IndoorTrend,
  type InvestigationResponse,
  type InvestigationSummary,
  type LawsResponse,
  type LivePowerResponse,
  type Notification,
  type NotificationAudience,
  type NotificationWhatsapp,
  type OutcomeHistoryEntry,
  type OutcomeResult,
  type OutcomeStatus,
  type Readiness,
  type ReadinessResult,
  type RecordedInvestigation,
  type RecordedReview,
  type ReplayMetrics,
  type ScenarioEvent,
  type SourceKind,
  type SourceStatus,
  type SourcesResponse,
  type TraceCheck,
  type TraceResponse,
  type VerificationHistoryEntry,
  type VerificationResult,
  type VerificationStage,
  type VisualEvidence,
  type WatcherResponse,
} from "./api";
import "./index.css";

const SCENARIOS = [
  { id: "care_home_v1", label: "Winter night, older adult at home (guided story)" },
  { id: "demo_v1", label: "No recovery" },
  { id: "demo_recovery_v1", label: "Manager report, late warming" },
  { id: "demo_no_followup_v1", label: "No follow-up readings" },
  { id: "demo_video_v1", label: "Trip home, thermostat offline (video)" },
  { id: "visual_water_low_temp_v1", label: "Water detection, low indoor temp (synthetic image)" },
  { id: "visual_frost_missed_v1", label: "Frost query missed, low indoor temp (synthetic image)" },
  { id: "visual_dry_floor_v1", label: "Dry floor, no detection (synthetic image)" },
];

const VIDEO_SCENARIO = "demo_video_v1";
const VIDEO_START_AT = "2026-01-16T16:31:00-05:00";

const CARE_SCENARIO = "care_home_v1";
const CARE_START_AT = "2026-01-16T19:03:00-05:00";

const REPLAY_START_AT = "2026-01-16T18:00:00-05:00";

const REPLAY_TIMES = [
  { label: "18:00", at: "2026-01-16T18:00:00-05:00" },
  { label: "18:30", at: "2026-01-16T18:30:00-05:00" },
  { label: "19:00", at: "2026-01-16T19:00:00-05:00" },
  { label: "20:31", at: "2026-01-16T20:31:00-05:00" },
];

const VIDEO_REPLAY_TIMES = [
  "09:20",
  "14:06",
  "16:31",
  "16:52",
  "18:21",
  "18:51",
  "19:51",
  "20:21",
  "20:46",
  "21:01",
].map((label) => ({ label, at: `2026-01-16T${label}:00-05:00` }));

const CARE_REPLAY_TIMES = [
  { day: "2026-01-16", label: "19:03" },
  { day: "2026-01-16", label: "19:15" },
  { day: "2026-01-16", label: "19:20" },
  { day: "2026-01-17", label: "02:31" },
  { day: "2026-01-17", label: "02:45" },
  { day: "2026-01-17", label: "04:21" },
  { day: "2026-01-17", label: "04:51" },
  { day: "2026-01-17", label: "06:21" },
  { day: "2026-01-17", label: "06:45" },
  { day: "2026-01-17", label: "07:01" },
].map(({ day, label }) => ({ label, at: `${day}T${label}:00-05:00` }));

const VERIFICATION_LABEL: Record<VerificationStage, string> = {
  telemetry_missing: "Thermostat telemetry missing",
  reporting_restored: "Thermostat reporting restored",
  warming_observed: "Warming observed",
  goal_verified: "Temperature goal verified",
  goal_not_maintained: "Temperature goal no longer maintained",
  arrival_met: "Warm-by expectation met",
  unable_to_verify: "Unable to verify",
};

const VERIFICATION_PROGRESSION: VerificationStage[] = [
  "reporting_restored",
  "warming_observed",
  "goal_verified",
  "arrival_met",
];

const VERIFICATION_ORDER: Partial<Record<VerificationStage, number>> = {
  reporting_restored: 0,
  warming_observed: 1,
  goal_verified: 2,
  arrival_met: 3,
};

const OUTCOME_LABEL: Record<OutcomeStatus, string> = {
  awaiting_measurement: "Waiting for new readings",
  warming_observed: "Warming observed",
  target_reached: "Target reached",
  not_observed_by_deadline: "No warming by the deadline",
  unable_to_verify: "Unable to verify: not enough readings",
};

const SOURCE_ORDER: SourceKind[] = ["calendar", "thermostat", "room_sensor", "electrical", "weather", "human_report"];

const AVAILABILITY_LABEL: Record<Availability, string> = {
  available: "Available",
  missing: "Missing",
  stale: "Stale",
  invalid: "Invalid",
  conflicting: "Conflicting",
};

const READINESS_LABEL: Record<Readiness, string> = {
  on_track: "On track",
  at_risk: "At risk",
  cannot_tell: "Cannot tell",
  arrival_passed: "Warm-by time passed",
};

function formatAge(age_s: number | null): string {
  if (age_s === null) return "No reading";
  if (age_s < 0) return "Timestamp is in the future";
  if (age_s < 60) return `${Math.round(age_s)}s old`;
  if (age_s < 3600) return `${Math.round(age_s / 60)}min old`;
  const hours = Math.floor(age_s / 3600);
  const minutes = Math.round((age_s % 3600) / 60);
  return minutes === 0 ? `${hours}h old` : `${hours}h ${minutes}min old`;
}

const PROPERTY_TIMEZONE = "America/New_York";

function startAtForScenario(scenarioId: string): string {
  if (scenarioId === VIDEO_SCENARIO) return VIDEO_START_AT;
  if (scenarioId === CARE_SCENARIO) return CARE_START_AT;
  return REPLAY_START_AT;
}

function formatTimestamp(value: string | null): string {
  if (!value) return "No reading";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : `${new Intl.DateTimeFormat("en-US", {
        timeZone: PROPERTY_TIMEZONE,
        year: "numeric",
        month: "numeric",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
        hour12: true,
      }).format(date)} ET`;
}

const PAYLOAD_LABELS: Record<string, string> = {
  audience: "Audience",
  kind: "Type",
  readiness: "Readiness",
  readiness_in_words: "Readiness summary",
  stage: "Stage",
  stage_in_words: "Stage summary",
  verified_facts: "Verified facts",
  what_was_done: "What was done",
  evaluated_at: "Evaluated at",
  planned_arrival: "Warm-by time",
  property_label: "Property",
  property: "Property",
  requested_action: "Requested action",
  access_note: "Access note",
  manager_contact_label: "Contact on file",
  manager_contact: "Contact on file",
  relevant_observations: "Relevant observations",
  observations: "Observations",
  label: "Label",
  landing: "Landing",
  consented: "Consented",
  asks: "Asks",
  acknowledgement: "Acknowledgement",
  physical_success: "Physical success",
  location: "Location",
  visit_end: "Visit end",
  reported_to_manager_at: "Reported to manager at",
  reported_to_caregiver_at: "Reported to caregiver at",
  caregiver_alert: "Caregiver alert",
  caregiver_hvac_authorized: "Caregiver authorized HVAC contact",
};

const EVENT_KIND_LABELS: Record<string, string> = {
  email_flight_confirmation: "Flight confirmation email",
  location_airport: "Airport location",
  confirmation_request: "Confirmation request",
  preparation_authorized: "Preparation authorized",
  scene_command: "Scene command",
  scene_acknowledged: "Scene acknowledged",
  location_unavailable: "Location unavailable",
  manager_alert: "Manager alert",
  manager_hvac_authorized: "Manager HVAC authorized",
  caregiver_alert: "Caregiver alert",
  caregiver_hvac_authorized: "Caregiver authorized HVAC contact",
  hvac_request: "HVAC request",
  service_visit: "Service visit",
  hvac_completion_report: "HVAC completion report",
};

const VALUE_LABELS: Record<string, string> = {
  homeowner: "Homeowner",
  property_manager: "Property manager",
  family_caregiver: "Family caregiver",
  hvac_company: "HVAC company",
  investigation_update: "Investigation update",
  manager_alert: "Manager alert",
  caregiver_alert: "Caregiver alert",
  caregiver_update_hvac_contacted: "Caregiver update: HVAC contacted",
  caregiver_update_goal_verified: "Caregiver update: temperature goal verified",
  informational: "For information",
  hvac_request: "HVAC request",
  on_track: "On track",
  at_risk: "At risk",
  cannot_tell: "Cannot tell",
  arrival_passed: "Warm-by time passed",
  telemetry_missing: "Thermostat telemetry missing",
  reporting_restored: "Thermostat reporting restored",
  warming_observed: "Warming observed",
  goal_verified: "Temperature goal verified",
  goal_not_maintained: "Temperature goal no longer maintained",
  arrival_met: "Warm-by expectation met",
  unable_to_verify: "Unable to verify",
};

function humanLabel(key: string): string {
  if (PAYLOAD_LABELS[key]) return PAYLOAD_LABELS[key];
  const spaced = key.replace(/_/g, " ");
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

function eventKindLabel(kind: string): string {
  if (EVENT_KIND_LABELS[kind]) return EVENT_KIND_LABELS[kind];
  const spaced = kind.replace(/_/g, " ");
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

function isEmptyValue(value: unknown): boolean {
  return value === null || value === undefined || value === "" || (Array.isArray(value) && value.length === 0);
}

function isIsoString(value: string): boolean {
  return /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(value) && !Number.isNaN(Date.parse(value));
}

function targetGapLine(summary: InvestigationSummary): string | null {
  const gap = summary.metrics?.target_gap;
  if (!gap) return null;
  return `Indoor ${gap.latest_value} ${gap.unit}, target ${gap.target_temp} ${gap.target_unit}`;
}

function ContextNotes({
  flags,
  deadlinePassed,
  scheduleStatus,
}: {
  flags: ContextFlags | null;
  deadlinePassed: boolean;
  scheduleStatus: string | null;
}) {
  const notes: string[] = [];
  if (flags?.trip_cancelled) notes.push("Context note: Warm-by plan cancelled.");
  if (flags?.trip_unconfirmed) notes.push("Context note: Warm-by plan or confirmation unconfirmed.");
  if (flags?.confirmation_outdated)
    notes.push("Context note: Outdated confirmation — confirmation is outdated for the current warm-by plan.");
  if (flags?.trip_mismatched)
    notes.push("Context note: Warm-by plan and confirmation mismatch — they do not match.");
  if (deadlinePassed) notes.push("Context note: Follow-up deadline passed (deadline_passed).");
  if (scheduleStatus) notes.push(`Follow-up schedule status: ${scheduleStatus}.`);
  if (notes.length === 0) return null;
  return (
    <div className="context-notes">
      {notes.map((note) => (
        <p key={note}>{note}</p>
      ))}
    </div>
  );
}

function ReadinessBlock({
  readiness,
  gapLine,
}: {
  readiness: ReadinessResult | null;
  gapLine: string | null;
}) {
  if (!readiness) return null;
  return (
    <div className="investigation-block readiness-block">
      <h3>Readiness</h3>
      <p className={`readiness readiness-${readiness.status}`}>
        Readiness: <strong>{READINESS_LABEL[readiness.status]}</strong>
        {gapLine ? `. ${gapLine}.` : "."}
      </p>
      {readiness.reasons.length > 0 && (
        <details className="readiness-details">
          <summary>Reasons ({readiness.reasons.length})</summary>
          <ul>
            {readiness.reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}

function VisualEvidencePanel({ scenario, at, enabled = true }: { scenario: string; at: string; enabled?: boolean }) {
  const [visual, setVisual] = useState<VisualEvidence | null | undefined>(undefined);
  const [readiness, setReadiness] = useState<ReadinessResult | null>(null);

  useEffect(() => {
    if (!enabled) return;
    let live = true;
    setVisual(undefined);
    setReadiness(null);
    fetchVisual(scenario, at)
      .then((response) => {
        if (!live || response.scenario !== scenario) return;
        setVisual(response.visual);
      })
      .catch(() => {
        if (live) setVisual(null);
      });
    fetchInvestigation(at, scenario)
      .then((response) => {
        if (live) setReadiness(response.readiness);
      })
      .catch(() => {
        if (live) setReadiness(null);
      });
    return () => {
      live = false;
    };
  }, [scenario, at, enabled]);

  if (visual === undefined) return <p role="status">Loading visual evidence…</p>;
  if (visual === null) return <p role="status">No visual evidence at this replay time.</p>;
  const dims = visual.boxes.length > 0 ? visual.boxes[0] : null;
  const stroke = dims ? Math.max(4, Math.round(dims.image_width / 250)) : 0;
  return (
    <div className="visual-evidence">
      <p>{visual.caption}</p>
      <div className="visual-frame" style={{ position: "relative", display: "inline-block", maxWidth: "100%" }}>
        <img src={visual.image_url} alt={visual.caption} style={{ display: "block", width: "100%", maxWidth: "480px", height: "auto" }} />
        {dims && (
          <svg
            viewBox={`0 0 ${dims.image_width} ${dims.image_height}`}
            preserveAspectRatio="none"
            style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}
            aria-hidden="true"
          >
            {visual.boxes.map((box) => (
              <rect
                key={box.index}
                x={box.x1}
                y={box.y1}
                width={box.x2 - box.x1}
                height={box.y2 - box.y1}
                fill="none"
                stroke="#ff5a5a"
                strokeWidth={stroke}
              />
            ))}
          </svg>
        )}
      </div>
      <p role="status">
        {visual.object_count === 0
          ? `No detection for ${visual.phrase} (synthetic image); absence of a detection is not an all-clear.`
          : `${visual.object_count} object${visual.object_count === 1 ? "" : "s"} detected for ${visual.phrase} (synthetic image).`}
      </p>
      {visual.object_count === 0 && visual.known_miss === true && (
        <p role="status">Missed by the model: this frame shows the condition, but the recorded segmentation found no object.</p>
      )}
      <ReadinessBlock readiness={readiness} gapLine={null} />
    </div>
  );
}

function PowerContextBlock({ summary }: { summary: InvestigationSummary }) {  const statement = summary.power_context_statement ?? summary.power_context?.statement;
  const limitations = summary.power_context?.limitations ?? [];
  if (!statement && limitations.length === 0) return null;
  return (
    <div className="power-context">
      <h3>Power context</h3>
      {statement && <p>{statement}</p>}
      {limitations.length > 0 && (
        <details className="limits-details">
          <summary>Limitations ({limitations.length})</summary>
          <ul>
            {limitations.map((limitation) => (
              <li key={limitation}>{limitation}</li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}

function ConfirmedPlanSection({ data, error }: { data: ContextResponse | null; error: string | null }) {
  if (error) {
    return (
      <p role="alert" className="error">
        Confirmed plan not reachable
      </p>
    );
  }
  if (!data) return <p role="status">Loading confirmed plan…</p>;
  const flags = data.context_flags ?? data.flags;
  if (!data.confirmed) {
    return (
      <div className="confirmed-plan">
        <p className="confirmed-plan-status">
          {flags?.confirmation_outdated ? "Confirmation outdated" : flags?.trip_cancelled ? "Warm-by plan cancelled" : flags?.trip_mismatched ? "Warm-by plan and confirmation do not match" : "Not yet confirmed"}
        </p>
        {data.reason_in_words && data.reason_in_words !== "Not yet confirmed" && <p>{data.reason_in_words}</p>}
        {flags?.confirmation_outdated && <p>Confirmation outdated for the current warm-by plan — the confirmed plan no longer matches the current revision.</p>}
        <p>
          Evaluation time: <time dateTime={data.at}>{formatTimestamp(data.at)}</time>
        </p>
      </div>
    );
  }
  const allowances = data.allowances ?? data.arrival_allowances ?? [];
  const target =
    data.target_temperature ??
    (data.target_temp !== undefined ? `${formatTargetTemp(data.target_temp)} ${data.target_unit ?? "F"}` : null);
  return (
    <div className="confirmed-plan">
      <dl className="card-facts">
        <div>
          <dt>Property</dt>
          <dd>{data.property_label ?? data.property_id ?? data.trip?.property_id ?? "—"}</dd>
        </div>
        {data.planned_arrival && (
          <div>
            <dt>Warm-by time</dt>
            <dd>
              <time dateTime={data.planned_arrival}>{formatTimestamp(data.planned_arrival)}</time>
            </dd>
          </div>
        )}
        {data.landing && (
          <div>
            <dt>Landing</dt>
            <dd>
              <time dateTime={data.landing}>{formatTimestamp(data.landing)}</time>
            </dd>
          </div>
        )}
        {allowances.map((allowance) => (
          <div key={allowance.kind}>
            <dt>{allowance.kind === "driving" ? "Driving allowance" : "Airport-exit/baggage allowance"}</dt>
            <dd>{allowance.label}</dd>
          </div>
        ))}
        {target && (
          <div className="key-plan-row">
            <dt>Target temperature</dt>
            <dd>{target}</dd>
          </div>
        )}
        <div>
          <dt>Homeowner notification</dt>
          <dd>{data.notify_homeowner ? "Yes — notify homeowner" : "No — do not notify homeowner"}</dd>
        </div>
        <div className="key-plan-row">
          <dt>{data.scenario === "care_home_v1" ? "Caregiver coordination" : "Manager coordination"}</dt>
          <dd>{data.manager_authorized ? `${data.scenario === "care_home_v1" ? "Caregiver" : "Manager"} coordination allowed` : `${data.scenario === "care_home_v1" ? "Caregiver" : "Manager"} coordination not allowed`}</dd>
        </div>
        {data.confirmed_at && (
          <div className="key-plan-row">
            <dt>Confirmed</dt>
            <dd>
              <time dateTime={data.confirmed_at}>{formatTimestamp(data.confirmed_at)}</time>
            </dd>
          </div>
        )}
        {data.revision_id && (
          <div>
            <dt>Revision</dt>
            <dd>{data.revision_id}</dd>
          </div>
        )}
      </dl>
      {allowances.length > 0 && <p>Planned times and allowances are scenario estimates, not live claims.</p>}
      {data.arrival_plan?.derivation && <p>{data.arrival_plan.derivation}</p>}
      <p>
        Evaluation time: <time dateTime={data.at}>{formatTimestamp(data.at)}</time>
      </p>
    </div>
  );
}

function InvestigationSection({
  data,
  error,
  created,
  replayAt,
  earlier = [],
}: {
  data: InvestigationResponse | null;
  error: string | null;
  created: CreateInvestigationResponse | null;
  replayAt: string | null;
  earlier?: RecordedInvestigation[];
}) {
  const earlierList = (earlier ?? []).filter(
    (item) =>
      !!item?.output && typeof item.evaluated_at === "string" &&
      replayAt !== null && !Number.isNaN(Date.parse(item.evaluated_at)) &&
      !Number.isNaN(Date.parse(replayAt)) && Date.parse(item.evaluated_at) < Date.parse(replayAt),
  );
  const earlierBlock =
    earlierList.length === 0 ? null : (
      <details className="earlier-explanations" data-testid="earlier-explanations">
        <summary>Earlier explanations ({earlierList.length})</summary>
        <p>Earlier recorded answers, kept as history. Only the answer above is current.</p>
        <ul>
          {earlierList.map((item) => (
            <li key={item.evaluated_at}>
              <p>
                Evaluation time: <time dateTime={item.evaluated_at}>{formatTimestamp(item.evaluated_at)}</time>
              </p>
              <p>{item.output?.interpretation}</p>
            </li>
          ))}
        </ul>
      </details>
    );
  if (!data && !error) return <p role="status">Loading investigation…</p>;
  if (error) {
    return (
      <p role="alert" className="error">
        Investigation not reachable
      </p>
    );
  }
  if (!data) return null;

  const gapLine = targetGapLine(data.summary);
  const computedReadiness = data.readiness ?? data.summary.readiness;
  const flags: ContextFlags =
    created?.context_flags ??
    created?.flags ??
    data.evidence_pack?.context_flags ??
    data.evidence_pack?.flags ??
    data.summary.readiness.inputs.flags;
  const deadlinePassed =
    created?.deadline_passed ??
    created?.follow_up_schedule?.deadline_passed ??
    data.output?.follow_up.deadline_passed ??
    false;
  const scheduleStatus =
    created?.schedule_status ??
    created?.follow_up_schedule?.status ??
    data.output?.follow_up.schedule_status ??
    null;
  const evaluatedAt =
    (data as { evaluated_at?: string }).evaluated_at ??
    created?.investigation?.evaluated_at ??
    data.evidence_pack?.at ??
    null;
  const isHistorical =
    evaluatedAt !== null &&
    replayAt !== null &&
    !Number.isNaN(Date.parse(evaluatedAt)) &&
    !Number.isNaN(Date.parse(replayAt)) &&
    Date.parse(evaluatedAt) < Date.parse(replayAt);
  const evaluationLine = evaluatedAt ? (
    <>
      <p className="investigation-evaluation-time">
        Evaluation time: <time dateTime={evaluatedAt}>{formatTimestamp(evaluatedAt)}</time>
      </p>
      {isHistorical && (
        <p className="historical-investigation" role="note">
          Historical investigation — evaluated earlier than the replay time{" "}
          <time dateTime={replayAt}>{formatTimestamp(replayAt)}</time>; this investigation was
          evaluated at an earlier time than the replay time.
        </p>
      )}
    </>
  ) : null;

  if (data.status === "rejected" || data.status === "unavailable" || !data.output) {
    return (
      <>
        {evaluationLine}
        {earlierBlock}
        <p className="unavailable">ARIA&apos;s explanation is unavailable</p>
        {data.status === "rejected" && (
          <p className="model-not-used">The model answer was not used.</p>
        )}
        {data.reasons.length > 0 && (
          <ul className="reasons">
            {data.reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        )}
        <div className="investigation-block deterministic-summary">
          <h3>Deterministic summary (computed by code)</h3>
          <ReadinessBlock readiness={data.summary.readiness} gapLine={gapLine} />
          <PowerContextBlock summary={data.summary} />
        </div>
        <ContextNotes flags={flags} deadlinePassed={deadlinePassed} scheduleStatus={scheduleStatus} />
        <p className="provenance">
          Provider mode: {data.provider_mode ?? "unknown"}, model: {data.model_id ?? "unknown"},
          prompt version: {data.prompt_version}
        </p>
      </>
    );
  }

  const output = data.output;
  return (
    <>
      {evaluationLine}
      {earlierBlock}
      {data.provider_mode === "mock" && (
        <p className="mock-label" role="note">
          MOCK - example answer, not live inference
        </p>
      )}

      <div className="investigation-block verified-facts">
        <h3>Verified facts (checked against the evidence)</h3>
        {output.verified_facts.length === 0 ? (
          <p>No verified facts reported.</p>
        ) : (
          <details className="facts-details">
            <summary>Facts ({output.verified_facts.length})</summary>
            <ul>
              {output.verified_facts.map((fact) => (
                <li key={fact}>{fact}</li>
              ))}
            </ul>
          </details>
        )}
      </div>

      <ReadinessBlock readiness={computedReadiness} gapLine={gapLine} />

      <div className="investigation-block interpretation">
        <h3>Interpretation (model-written, not verified)</h3>
        <p>{output.interpretation}</p>
        {output.limitations.length > 0 && (
          <details className="limits-details">
            <summary>Limitations ({output.limitations.length})</summary>
            <ul>
              {output.limitations.map((limitation) => (
                <li key={limitation}>{limitation}</li>
              ))}
            </ul>
          </details>
        )}
      </div>

      <details className="investigation-details">
        <summary>Possible explanations (not confirmed)</summary>
        <div className="investigation-block possible-explanations">
          {output.hypotheses.length === 0 ? (
            <p>No hypotheses reported.</p>
          ) : (
            <ul className="hypotheses">
              {output.hypotheses.map((hypothesis, index) => (
                <li key={`${hypothesis.text}-${index}`}>
                  <p className="hypothesis-label">{hypothesis.text}</p>
                  {hypothesis.supporting_ids.length > 0 && (
                    <p>
                      Supporting:{" "}
                      {hypothesis.supporting_ids.map((id) => (
                        <span key={id} className="chip">
                          {id}
                        </span>
                      ))}
                    </p>
                  )}
                  {hypothesis.conflicting_ids.length > 0 && (
                    <p>
                      Conflicting:{" "}
                      {hypothesis.conflicting_ids.map((id) => (
                        <span key={id} className="chip">
                          {id}
                        </span>
                      ))}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </details>

      <ContextNotes flags={flags} deadlinePassed={deadlinePassed} scheduleStatus={scheduleStatus} />

      <details className="investigation-details">
        <summary>What we don&apos;t know</summary>
        {output.unknowns.length === 0 ? (
          <p>Nothing listed.</p>
        ) : (
          <ul>
            {output.unknowns.map((unknown) => (
              <li key={unknown}>{unknown}</li>
            ))}
          </ul>
        )}
      </details>

      <details className="investigation-details">
        <summary>One question for you</summary>
        <h3>One question for you</h3>
        <p>{output.clarification}</p>
      </details>

      <details className="investigation-details">
        <summary>Next check</summary>
        <h3>Next check</h3>
        <p>
          {output.follow_up.observation}
          {output.follow_up.when ? ` (${formatTimestamp(output.follow_up.when)})` : ""}
        </p>
      </details>

      <details className="investigation-details">
        <summary>Power context</summary>
        <PowerContextBlock summary={data.summary} />
      </details>

      <p className="provenance">
        Provider mode: {data.provider_mode ?? "unknown"}, model: {data.model_id ?? "unknown"},
        prompt version: {data.prompt_version}
      </p>
      {data.recorded_review && (
        <details className="recorded-review-details">
          <summary>Second review (recorded)</summary>
          <RecordedReviewBlock recordedReview={data.recorded_review} />
        </details>
      )}
    </>
  );
}

function OutcomeSection({
  outcome,
  history,
  verificationHistory,
  replayAt,
  unit,
  error,
  loading,
  verification,
  notScheduled,
}: {
  outcome: OutcomeResult | null;
  history: OutcomeHistoryEntry[];
  verificationHistory: VerificationHistoryEntry[];
  replayAt: string | null;
  unit: string | null;
  error: string | null;
  loading: boolean;
  verification: VerificationResult | null;
  notScheduled: boolean;
}) {
  if (!outcome) {
    if (notScheduled) {
      return (
        <p className="outcome-status" aria-live="polite">
          Status: <strong>No follow-up scheduled yet</strong>
        </p>
      );
    }
    if (!error) return <p role="status">Loading outcome…</p>;
    return (
      <p role="alert" className="error">
        {error ?? "Follow-up not reachable"}
      </p>
    );
  }
  const valueUnit = unit ? ` °${unit}` : "";
  const stageOrder = verification ? VERIFICATION_ORDER[verification.stage] : undefined;
  const latestReading = verification?.latest_reading_used ?? null;
  return (
    <div className={`outcome outcome-${outcome.status}`}>
      {loading && <p role="status">Loading outcome…</p>}
      {error && (
        <p role="alert" className="error">
          Follow-up refresh failed
        </p>
      )}
      {verification ? (
        <>
          <p className="outcome-status verification-stage" aria-live="polite">
            Status: <strong>{VERIFICATION_LABEL[verification.stage]}</strong>
          </p>
          <p className="follow-up-rule">Follow-up rule: {OUTCOME_LABEL[outcome.status]}</p>
          {latestReading ? (
            <p className="latest-reading-used">
              Latest reading used: observed{" "}
              <time dateTime={latestReading.observed_at}>{formatTimestamp(latestReading.observed_at)}</time>{" "}
              received{" "}
              <time dateTime={latestReading.received_at}>{formatTimestamp(latestReading.received_at)}</time>
            </p>
          ) : (
            <p className="latest-reading-used">Latest reading used: No reading</p>
          )}
          <dl className="outcome-facts stage-times">
            <div>
              <dt>Evaluation (replay) time</dt>
              <dd>
                <time dateTime={verification.evaluated_at}>{formatTimestamp(verification.evaluated_at)}</time>
              </dd>
            </div>
          </dl>
          <ol className="verification-progression">
            {VERIFICATION_PROGRESSION.map((stage, index) => {
              const reached = stageOrder !== undefined && index <= stageOrder;
              return (
                <li key={stage}>
                  {VERIFICATION_LABEL[stage]} — {reached ? "Reached" : "Not reached"}
                </li>
              );
            })}
          </ol>
        </>
      ) : (
        <p className="outcome-status" aria-live="polite">
          Status: <strong>{OUTCOME_LABEL[outcome.status]}</strong>
        </p>
      )}
      {replayAt && (
        <p className="outcome-time">
          Replay time: <time dateTime={replayAt}>{formatTimestamp(replayAt)}</time>
        </p>
      )}
      <dl className="outcome-facts">
        <div>
          <dt>Readings</dt>
          <dd>{outcome.sample_count}</dd>
        </div>
        <div>
          <dt>First value</dt>
          <dd>{outcome.first_value === null ? "No reading" : `${outcome.first_value}${valueUnit}`}</dd>
        </div>
        <div>
          <dt>Last value</dt>
          <dd>{outcome.last_value === null ? "No reading" : `${outcome.last_value}${valueUnit}`}</dd>
        </div>
      </dl>
      {outcome.note && <p className="outcome-note">{outcome.note}</p>}
      <details className="history-details">
        <summary>History</summary>
        {verification ? (
        verificationHistory.length === 0 ? (
          <p>No replay steps yet.</p>
        ) : (
          <ul className="outcome-history">
            {verificationHistory.map((entry) => (
              <li key={entry.evaluated_at}>
                <time dateTime={entry.evaluated_at}>{formatTimestamp(entry.evaluated_at)}</time>
                {" — "}
                {VERIFICATION_LABEL[entry.stage]}
                {entry.sample_count !== null ? ` (${entry.sample_count} readings)` : ""}
              </li>
            ))}
          </ul>
        )
      ) : history.length === 0 ? (
        <p>No replay steps yet.</p>
      ) : (
        <ul className="outcome-history">
          {history.map((entry) => (
            <li key={entry.evaluated_at}>
              <time dateTime={entry.evaluated_at}>{formatTimestamp(entry.evaluated_at)}</time>
              {" — "}
              {OUTCOME_LABEL[entry.status]} ({entry.sample_count} readings)
            </li>
          ))}
        </ul>
      )}
      </details>
    </div>
  );
}

function EvidenceTimelineSection({ entries }: { entries: EvidenceTimelineEntry[] }) {
  if (entries.length === 0) return <p>No evidence timeline entries yet.</p>;
  return (
    <details className="evidence-details">
      <summary>Show all {entries.length} entries</summary>
      <ol className="evidence-timeline">
        {entries.map((entry) => (
          <li key={entry.kind} className="evidence-timeline-entry">
            <p className="evidence-timeline-label">{entry.label}</p>
            {entry.corroboration_only && <p className="corroboration-only">Corroboration only</p>}
            <details className="evidence-details">
              <summary>Entry details</summary>
              <dl className="card-facts">
                <div>
                  <dt>Observed</dt>
                  <dd>
                    <time dateTime={entry.observed_at}>{formatTimestamp(entry.observed_at)}</time>
                  </dd>
                </div>
                <div>
                  <dt>Received / available</dt>
                  <dd>
                    <time dateTime={entry.received_at}>{formatTimestamp(entry.received_at)}</time>
                  </dd>
                </div>
                <div>
                  <dt>First known (evaluation)</dt>
                  <dd>
                    <time dateTime={entry.first_known_at}>{formatTimestamp(entry.first_known_at)}</time>
                  </dd>
                </div>
              </dl>
              <p className="supporting-ids">Supporting records: {entry.supporting_ids.join(", ")}</p>
            </details>
          </li>
        ))}
      </ol>
    </details>
  );
}

function RecordedReviewBlock({ recordedReview }: { recordedReview: RecordedReview }) {
  const { review, provenance } = recordedReview;
  const legacy = recordedReview.answer_bound === false;
  const mismatch = recordedReview.answer_mismatch === true;
  return (
    <div className="investigation-block recorded-review">
      {legacy && (
        <p role="note">Review recorded before answer binding (legacy, not bound to this exact answer)</p>
      )}
      {mismatch && <p role="note">Review does not match this answer — no review shown.</p>}
      {review ? (
        <>
          <p className="review-verdict-line">
            <strong>Second review (muse-wonder-1.0, recorded):</strong>{" "}
            {review.verdict === "no_issues" ? "no issues found" : "issues found"}
            {review.verdict === "no_issues" && " — not verification of the home."}
          </p>
          {review.issues.length > 0 && (
            <ul>
              {review.issues.map((issue, index) => (
                <li key={`${issue.kind}-${index}`}>
                  {issue.kind} — {issue.note} (evidence: {issue.evidence_ids.join(", ") || "none"})
                </li>
              ))}
            </ul>
          )}
        </>
      ) : (
        !mismatch && <p role="note">The recorded review is invalid and changes nothing.</p>
      )}
      <p className="provenance">
        Model: {provenance.model_id} — route {provenance.provider_route}, recorded{" "}
        {provenance.recorded_at ?? "unknown"}, reviewing {provenance.reviewed_model_id ?? "unknown"} at{" "}
        {provenance.reviewed_at ?? "unknown"}. Validation:{" "}
        {provenance.validation.passed ? "passed" : `failed — ${provenance.validation.reasons.join("; ")}`}
      </p>
      <p className="corroboration-only">A matching review is a bounded check, not proof the narrative is true. A review never changes readiness, verification, or the answer.</p>
    </div>
  );
}

function HumanReportSection({ report }: { report: HumanReportPayload | null }) {
  if (!report) return null;
  return (
    <div className="investigation-block human-report">
      <h3>Technician voice-note report</h3>
      <p>{report.transcript}</p>
      <p className="corroboration-only">Human report, not a sensor measurement. Corroboration only.</p>
      <dl className="card-facts">
        <div>
          <dt>Observed</dt>
          <dd>
            <time dateTime={report.observed_at}>{formatTimestamp(report.observed_at)}</time>
          </dd>
        </div>
        <div>
          <dt>Received</dt>
          <dd>
            <time dateTime={report.received_at}>{formatTimestamp(report.received_at)}</time>
          </dd>
        </div>
      </dl>
      <p className="provenance">
        Model: {report.provenance.model_id} — route {report.provenance.provider_route}, recorded{" "}
        {report.provenance.recorded_at ?? "unknown"}, audio fixture {report.provenance.audio_fixture}.
      </p>
    </div>
  );
}

function EvidenceSourcesTable({ sources }: { sources: SourceStatus[] }) {
  const ordered = SOURCE_ORDER.map((source) => sources.find((s) => s.source === source)).filter(
    (status): status is SourceStatus => status !== undefined,
  );
  return (
    <div className="evidence-table-wrap">
      <table className="evidence-table">
        <thead>
          <tr>
            <th scope="col">Source</th>
            <th scope="col">Status</th>
            <th scope="col">Latest reading</th>
            <th scope="col">Freshness</th>
          </tr>
        </thead>
        <tbody>
          {ordered.map((status) => {
            const missing = status.availability === "missing" || status.newest_observed_at === null;
            const newestValue =
              status.newest_value === null || status.newest_value === undefined
                ? null
                : `${status.newest_value}${status.newest_unit ? ` ${status.newest_unit}` : ""}`;
            return (
              <tr key={status.source} data-source={status.source} className={`availability-${status.availability}`}>
                <td>{status.source}</td>
                <td>
                  <span className="dot" aria-hidden="true" /> Status:{" "}
                  <strong>{AVAILABILITY_LABEL[status.availability]}</strong>
                </td>
                <td>{newestValue ?? "No reading"}</td>
                <td>
                  newest observed {formatTimestamp(status.newest_observed_at)}, age{" "}
                  {formatAge(status.age_s)}
                  {(status.missing_count ?? 0) > 0 ? ` (Missing readings: ${status.missing_count})` : ""}
                  {status.source === "weather" && !missing ? " Forecast, not an on-property measurement." : ""}
                  {status.source === "human_report" ? " Human report, not a sensor measurement." : ""}
                  {status.notes.length > 0 && (
                    <details className="source-notes-details">
                      <summary>Notes ({status.notes.length})</summary>
                      <p>{status.notes.join("; ")}</p>
                    </details>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function formatPayloadValue(value: unknown): string {
  if (Array.isArray(value)) return value.map((item) => formatPayloadValue(item)).join("; ");
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") return String(value);
  if (value !== null && typeof value === "object") {
    return Object.entries(value as Record<string, unknown>)
      .filter(([, v]) => !isEmptyValue(v))
      .map(([k, v]) => `${humanLabel(k)}: ${formatPayloadValue(v)}`)
      .join("; ");
  }
  if (typeof value === "string") {
    if (isIsoString(value)) return formatTimestamp(value);
    if (VALUE_LABELS[value]) return VALUE_LABELS[value];
    if (/^[a-z][a-z0-9]*(_[a-z0-9]+)+$/.test(value)) {
      const spaced = value.replace(/_/g, " ");
      return spaced.charAt(0).toUpperCase() + spaced.slice(1);
    }
    return value;
  }
  return String(value);
}

function formatWatcherValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "string") return value === "" ? "—" : value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) {
    if (value.length === 0) return "none";
    return value.map((item) => formatWatcherValue(item)).join("; ");
  }
  if (typeof value === "object") {
    const record = value as Record<string, unknown>;
    if (typeof record.kind === "string" && "claim" in record) {
      const evidence = Array.isArray(record.evidence_ids)
        ? ` (${record.evidence_ids.map((id) => String(id)).join(", ") || "none"})`
        : "";
      return `${record.kind}: ${formatWatcherValue(record.claim)}${evidence}`;
    }
    if (typeof record.rule === "string" && "detail" in record) {
      return `${record.rule}: ${formatWatcherValue(record.detail)}`;
    }
    try {
      return JSON.stringify(value);
    } catch {
      return String(value);
    }
  }
  return String(value);
}

class SectionBoundary extends Component<{ name: string; children: ReactNode }, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError(): { failed: boolean } {
    return { failed: true };
  }

  render() {
    if (this.state.failed) {
      return (
        <p role="alert" className="error">
          This section could not be shown ({this.props.name}).
        </p>
      );
    }
    return this.props.children;
  }
}

function PayloadFacts({ payload }: { payload: Record<string, unknown> }) {
  const entries = Object.entries(payload).filter(([, value]) => !isEmptyValue(value));
  const keys = Object.keys(payload);
  return (
    <>
      <dl className="card-facts">
        {entries.map(([key, value]) => (
          <div key={key}>
            <dt>{humanLabel(key)}</dt>
            <dd>{formatPayloadValue(value)}</dd>
          </div>
        ))}
      </dl>
      <p className="fields-sent">fields sent: {keys.join(", ")}</p>
    </>
  );
}

function SimulatedTimeline({ events, replayAt }: { events: ScenarioEvent[]; replayAt: string | null }) {
  return (
    <>
      {replayAt && (
        <p className="eval-time">
          Evaluation (replay) time: <time dateTime={replayAt}>{formatTimestamp(replayAt)}</time>
        </p>
      )}
      {events.length === 0 ? (
        <p>No simulated events visible.</p>
      ) : (
        <details className="events-details">
          <summary>Show all {events.length} simulated events</summary>
          <div className="event-cards">
            {events.map((event) => (
            <article key={event.id} className="event-card" aria-label={`${eventKindLabel(event.kind)} event`}>
              <h3 className="card-title">{eventKindLabel(event.kind)}</h3>
              <p className="simulated-tag">SIMULATED</p>
              <dl className="card-facts">
                <div>
                  <dt>Event time</dt>
                  <dd>
                    <time dateTime={event.event_time}>{formatTimestamp(event.event_time)}</time>
                  </dd>
                </div>
                <div>
                  <dt>Available time (received time)</dt>
                  <dd>
                    <time dateTime={event.available_at}>{formatTimestamp(event.available_at)}</time>
                  </dd>
                </div>
              </dl>
              {event.kind === "scene_acknowledged" && <p>Acknowledged, physical success unknown</p>}
              {event.kind === "hvac_completion_report" && (
                <p>Corroboration only, does not set the outcome</p>
              )}
              <PayloadFacts payload={event.payload} />
            </article>
          ))}
          </div>
        </details>
      )}
    </>
  );
}

const NOTIFICATION_AUDIENCE_LABEL: Record<NotificationAudience, string> = {
  homeowner: "Homeowner",
  property_manager: "Property manager",
  family_caregiver: "Family caregiver",
  hvac_company: "HVAC company",
};

const REFUSAL_REASON_LABEL: Record<string, string> = {
  manager_not_authorized: "property manager not authorized",
  manager_hvac_not_authorized: "manager has not authorized HVAC contact",
  caregiver_not_authorized: "family caregiver not authorized",
  caregiver_hvac_not_authorized: "caregiver has not authorized HVAC contact",
  caregiver_declined: "the caregiver declined HVAC contact",
};

function refusalReasonInWords(notification: Notification): string {
  const reason = notification.refusal_reason ?? notification.reason ?? "not authorized";
  return REFUSAL_REASON_LABEL[reason] ?? reason.replace(/_/g, " ");
}

function whatsappLine(whatsapp: NotificationWhatsapp | null | undefined): string {
  const state = whatsapp?.state ?? "";
  if (state === "accepted_by_api") {
    const id = whatsapp?.message_id ? ` (message id ${whatsapp.message_id})` : "";
    return `Accepted by the WhatsApp API${id}; delivery to the handset is not confirmed`;
  }
  if (state.startsWith("unknown:")) {
    return `Delivery unknown (${state.slice("unknown:".length)}); check the test phone manually — the app never resends`;
  }
  if (state.startsWith("failed:")) {
    return `Delivery failed (${state.slice("failed:".length)}); the notice stays simulated`;
  }
  return "Simulated, no message was sent";
}

function notificationStateInWords(notification: Notification): string {
  if (notification.state === "refused") return `Refused: ${refusalReasonInWords(notification)}`;
  if (notification.state === "simulated_delivered") return "Simulated delivery";
  if (notification.state === "queued") return "Simulated delivery";
  return notification.state.replace(/_/g, " ");
}

function caregiverStatusParts(permission: CaregiverPermission): {
  prefix: string;
  whenText: string;
  whenDateTime: string | null;
  effect: string;
} {
  if (permission.status === "approved") {
    return {
      prefix: "Approved by the caregiver at",
      whenText: permission.decided_at ? formatTimestamp(permission.decided_at) : "an unknown time",
      whenDateTime: permission.decided_at ?? null,
      effect: "HVAC may now be contacted.",
    };
  }
  if (permission.status === "declined") {
    return {
      prefix: "Declined by the caregiver at",
      whenText: permission.decided_at ? formatTimestamp(permission.decided_at) : "an unknown time",
      whenDateTime: permission.decided_at ?? null,
      effect: "No HVAC request; ARIA keeps monitoring.",
    };
  }
  return {
    prefix: "No answer yet — asked at",
    whenText: permission.requested_at ? formatTimestamp(permission.requested_at) : "an unknown time",
    whenDateTime: null,
    effect: "ARIA will not contact HVAC until she answers.",
  };
}

function caregiverStatusCopy(permission: CaregiverPermission): { headline: string; effect: string } {
  const parts = caregiverStatusParts(permission);
  return { headline: `${parts.prefix} ${parts.whenText}.`, effect: parts.effect };
}

function CaregiverPermissionCard({
  permission,
  onDecide,
  deciding,
  whatsappConfigured,
  onSendWhatsapp,
  sending,
}: {
  permission: CaregiverPermission;
  onDecide: (decision: "approve" | "decline") => void;
  deciding: boolean;
  whatsappConfigured: boolean;
  onSendWhatsapp: () => void;
  sending: boolean;
}) {
  const copy = caregiverStatusCopy(permission);
  const parts = caregiverStatusParts(permission);
  const dotTone = permission.status === "approved" ? "ok" : permission.status === "declined" ? "risk" : "watch";
  return (
    <article className="caregiver-permission-card" aria-label="Caregiver permission" data-testid="caregiver-permission">
      <h3 className="card-title">Permission request to the family caregiver</h3>
      <blockquote className="permission-text">{permission.text}</blockquote>
      <p className="permission-asked">
        Asked at <time dateTime={permission.requested_at}>{formatTimestamp(permission.requested_at)}</time> — the
        original request, kept word-for-word at every later step.
      </p>
      <p className={`permission-status permission-${permission.status}`} role="status">
        <span className={`status-dot status-dot-${dotTone}`} aria-hidden="true" /> {parts.prefix}{" "}
        {parts.whenDateTime ? (
          <time dateTime={parts.whenDateTime}>{parts.whenText}</time>
        ) : (
          parts.whenText
        )}
        . {copy.effect}
        {permission.source && <span className="permission-source"> ({permission.source})</span>}
      </p>
      <p className="permission-note">{permission.note}</p>
      {permission.status === "waiting" && (
        <div className="permission-actions">
          <button type="button" className="btn-primary" onClick={() => onDecide("approve")} disabled={deciding}>
            Approve (as the caregiver)
          </button>
          <button type="button" className="ghost-button" onClick={() => onDecide("decline")} disabled={deciding}>
            Decline (as the caregiver)
          </button>
          {whatsappConfigured && (
            <button type="button" className="ghost-button" onClick={onSendWhatsapp} disabled={sending}>
              Send this request to my test phone (WhatsApp)
            </button>
          )}
        </div>
      )}
    </article>
  );
}

function LiveCameraPanel() {
  const [snapshot, setSnapshot] = useState<CameraSnapshotResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function take(segment: boolean) {
    setBusy(true);
    setError(null);
    takeCameraSnapshot(segment)
      .then((response) => {
        setSnapshot(response);
        setBusy(false);
      })
      .catch(() => {
        setError("Camera not reachable");
        setBusy(false);
      });
  }

  return (
    <div className="live-camera-panel" data-testid="live-camera">
      <p className="live-camera-note">
        One frame on request from the owner&rsquo;s Nest camera. It is never evidence for the synthetic story&rsquo;s readiness or verification.
      </p>
      <div className="permission-actions">
        <button type="button" className="ghost-button" onClick={() => take(false)} disabled={busy}>
          Take one snapshot
        </button>
        <button type="button" className="ghost-button" onClick={() => take(true)} disabled={busy}>
          Take one snapshot and send it to sam-3.1
        </button>
      </div>
      <p className="live-camera-note">The second button uploads that one real image to Meta&rsquo;s sam-3.1 to look for frost, a water puddle and an indicator light.</p>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {snapshot && (
        <div className="live-camera-result" role="status">
          <p>
            {snapshot.camera.status === "ok" ? "Snapshot taken" : `Snapshot not taken: ${snapshot.camera.status}`}
            {snapshot.camera.device_display_name ? ` (${snapshot.camera.device_display_name})` : ""} at{" "}
            <time dateTime={snapshot.camera.captured_at}>{formatTimestamp(snapshot.camera.captured_at)}</time>
          </p>
          {snapshot.image_url && <img src={snapshot.image_url} alt="Latest frame from the owner's mechanical-room camera" className="live-camera-image" />}
          {snapshot.segmentation && (
            <div>
              <p>
                <strong>{snapshot.segmentation.disclosure ?? snapshot.segmentation.reason}</strong>
              </p>
              <ul>
                {(snapshot.segmentation.results ?? []).map((item) => (
                  <li key={item.phrase}>
                    {item.phrase}: {item.status === "ok" ? `${item.count} found${item.note ? ` (${item.note})` : ""}` : `failed (${item.error ?? "error"})`}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function formatTargetTemp(value: number): string {
  return Number.isInteger(value) ? String(value) : String(value);
}

function HomeownerUpdateCard({
  verification,
  targetTemp,
  targetUnit,
  verifiedFacts,
  sectionClassName,
}: {
  verification: VerificationResult | null;
  targetTemp: number | null;
  targetUnit: string | null;
  verifiedFacts: string[];
  sectionClassName?: string;
}) {
  if (!verification || verification.stage !== "arrival_met" || targetTemp === null) return null;
  const unit = targetUnit ?? "F";
  const tempLabel = `${formatTargetTemp(targetTemp)} ${unit}`;
  const factsSupport =
    verifiedFacts.length > 0 ||
    verification.reasons.some((reason) => reason.includes(tempLabel) || reason.includes(String(targetTemp)));
  if (!factsSupport && verification.supporting_ids.length === 0) return null;
  return (
    <section aria-labelledby="homeowner-update-heading" className={sectionClassName}>
      <h2 id="homeowner-update-heading">Homeowner update</h2>
      <article className="homeowner-update-card" aria-label="Homeowner update">
        <p className="homeowner-update">
          Your home reached and held {tempLabel} before the warm-by time
        </p>
        <p>
          Evaluation time:{" "}
          <time dateTime={verification.evaluated_at}>{formatTimestamp(verification.evaluated_at)}</time>
        </p>
      </article>
    </section>
  );
}

function LivePowerPanel({ data }: { data: LivePowerResponse }) {
  return (
    <div aria-live="polite">
      <p>
        {data.source} — read-only, display only
      </p>
      {data.fetched_at && (
        <p className="eval-time">
          Read at: <time dateTime={data.fetched_at}>{formatTimestamp(data.fetched_at)}</time>
          {data.cached ? " (cached)" : ""}
        </p>
      )}
      {data.circuits.length === 0 ? (
        <p>No circuits reported.</p>
      ) : (
        <dl className="card-facts">
          {data.circuits.map((circuit) => (
            <div key={circuit.circuit}>
              <dt>{circuit.circuit}</dt>
              <dd>{circuit.watts} W</dd>
            </div>
          ))}
        </dl>
      )}
      <p>Watts are not heat: live power never feeds readiness, warming, or verification.</p>
    </div>
  );
}

const INSET_TARGETS: Record<string, string[]> = {
  plan: ["plan"],
  timeline: ["timeline"],
  trip: ["timeline"],
  outcome: ["outcome"],
  notifications: ["notifications"],
  investigation: ["investigation"],
  homeowner: ["homeowner"],
  evidence: ["evidence"],
  visual: ["visual"],
  "not-responding": ["outcome", "investigation"],
  arrival: ["outcome", "homeowner"],
  "evidence-timeline": ["evidence-timeline"],
};

const KEY_CAPTIONS: Record<string, string> = {
  "k-plan": "Replay time: 7:20 PM ET",
  "k-confirm": "Replay time: 7:20 PM ET",
  "k-flag": "Replay time: 2:31 AM ET",
  "k-auth": "Replay time: 2:45 AM ET",
  "k-ack": "Replay time: 2:45 AM ET",
  "k-restored": "Replay time: 4:21 AM ET",
  "k-warming": "Replay time: 4:51 AM ET",
  "k-verified": "Replay time: 6:21 AM ET",
  "k-arrival": "Replay time: 7:01 AM ET",
  "k-report": "Replay time: 6:45 AM ET",
  "k-home": "Replay time: 7:01 AM ET",
};

const PUBLIC_DISCLOSURE =
  "Interactive demo · Synthetic home data · Simulated notifications · Recorded model responses where indicated · No equipment control.";

const BRAD_HOOK =
  "I live in Petoskey, Michigan, where the winters are long and cold. As my in-laws get older, I've started wondering what happens when they can't fix something, or can't tell that something is wrong, and nobody is around to help. As an electrician, I've worked on houses with major damage from a fault that nobody caught in time. ARIA Home is built to notice sooner and get the right person moving. It does not repair or control anything, and it is not a medical or emergency service.";

const STORY_SCENARIO = "care_home_v1";

const STORY_STEP_TITLES = [
  "Warm-by plan confirmed, with consent",
  "Confirmation requested",
  "House cooling overnight",
  "Flagged before the warm-by time",
  "Caregiver approves HVAC contact",
  "Thermostat reporting restored",
  "Warming observed",
  "Temperature goal verified",
  "Completion report as corroboration",
  "Warm-by expectation met",
];

const STORY_STEP_GUIDANCE = [
  "An older adult lives alone in demo-house. The household warm-by expectation is 07:00 at 68 F, recorded with the resident's consent: home status and observations may go to the resident and an adult-child family caregiver, nothing medical, no location tracking, no fall sensing.",
  "ARIA Home asks for confirmation of the property, the warm-by plan, the target temperature, and caregiver coordination; the plan is confirmed at 19:20 with caregiver coordination allowed.",
  "Overnight the furnace stops and the thermostat stops reporting; an independent room sensor shows the living area cooling toward 52 F.",
  "ARIA Home flags the risk before the 07:00 warm-by time and notifies the resident and the family caregiver. Only scoped audiences are notified: the caregiver notice carries allowed fields only. ARIA then asks the caregiver: may it contact the HVAC company? Try Approve or Decline on the permission card: HVAC is contacted only after approval, and the Outcome headline never changes.",
  "The caregiver explicitly authorizes contacting the HVAC company on file (in the recorded story, unless you declined at the previous step); only then is the simulated HVAC request allowed, carrying property, access note, and observations only, and the caregiver is told it was sent.",
  "Thermostat reporting is restored, but reconnection alone proves nothing; verification is still pending.",
  "Independent room readings show warming; the thermostat trend alone never decides this.",
  "Independent readings held the 68 F goal through the full 30-minute hold: verified before the warm-by time, with the reading and evaluation times shown.",
  "The HVAC completion report arrives after verification, as corroboration only; it changes no outcome.",
  "The warm-by time is evaluated from readings received by 07:00, not assumed from verification.",
];

const MODEL_CONTRIBUTIONS = [
  {
    model: "muse-spark-1.3",
    role: "Runtime explanation of the computed status",
    status: "Recorded here where a matching recording exists, otherwise the deterministic summary is shown",
  },
  {
    model: "sam-3.1",
    role: "Recorded segmentation of the synthetic images, including the missed frost",
    status: "Replay-only; never called at runtime",
  },
  {
    model: "muse-image-1.0",
    role: "Generated the synthetic images only",
    status: "Fixture generation; not a runtime integration",
  },
  {
    model: "muse-wonder-1.0 (second review)",
    role: "Recorded structured second review of a displayed muse-spark-1.3 answer",
    status: "Bound to the exact displayed answer; legacy reviews are labelled unbound; never changes readiness, verification, or validity",
  },
  {
    model: "muse-voice-transcribe-1.0 (human report)",
    role: "Recorded transcript of the synthetic technician voice note as a human-report record",
    status: "Corroboration only; never a measurement, outcome, or verification input",
  },
  {
    model: "muse-spark-1.3 (anomaly watcher)",
    role: "Recorded anomaly observations over the same evidence, each confirmed by the evidence check",
    status: "Shown on the Laws view with code detections and provenance; never lowers risk",
  },
  {
    model: "muse-wonder-1.0 and muse-spark-1.3",
    role: "Wrote the application code",
    status: "Authorship; no runtime role",
  },
];

const NO_RECORDED_LABEL = "No recorded model response for this snapshot";

function LawsView({ scenario, at, onBack, active }: { scenario: string; at: string; onBack: () => void; active: boolean }) {
  const [laws, setLaws] = useState<LawsResponse | null>(null);
  const [watcher, setWatcher] = useState<WatcherResponse | null>(null);
  const [corrections, setCorrections] = useState<CorrectionsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    setError(null);
    Promise.all([fetchLaws(), fetchWatcher(scenario, at), fetchCorrections()])
      .then(([lawsResponse, watcherResponse, correctionsResponse]) => {
        if (cancelled) return;
        setLaws(lawsResponse);
        setWatcher(watcherResponse);
        setCorrections(correctionsResponse);
      })
      .catch(() => {
        if (!cancelled) setError("Laws data not reachable");
      });
    return () => {
      cancelled = true;
    };
  }, [scenario, at, active]);

  return (
    <section aria-labelledby="laws-heading">
      <h2 id="laws-heading">ARIA&rsquo;s Laws</h2>
      <p>
        Every model output is checked by code. A violation rejects the output and names the law. Proposed
        laws never enforce.
      </p>
      <button type="button" className="ghost-button" onClick={onBack}>
        Back to investigation
      </button>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {!laws ? (
        <p role="status">Loading laws…</p>
      ) : (
        <>
          <details className="laws-details">
            <summary>Model laws (version {laws.version}, {laws.model_laws.length})</summary>
            <ul className="laws-compact">
              {laws.model_laws.map((law) => (
                <li key={law.id}>
                  <strong>{law.id}</strong> — {law.statement} [{law.status}
                  {law.status === "proposed" ? ", never enforced" : ""}
                  ; rejected {law.rejected_recorded} recorded output{law.rejected_recorded === 1 ? "" : "s"}]
                </li>
              ))}
            </ul>
          </details>
          <details className="laws-details">
            <summary>Process laws ({laws.process_laws.length})</summary>
            <ul className="laws-compact">
              {laws.process_laws.map((law) => (
                <li key={law.id}>
                  <strong>{law.id}</strong> — {law.statement} (stage: {law.stage}; check:{" "}
                  {law.check_status})
                </li>
              ))}
            </ul>
          </details>
        </>
      )}
      <details className="laws-details">
        <summary>Watcher observations (recorded only)</summary>
      {!watcher ? (
        <p role="status">Loading watcher…</p>
      ) : (
        <>
          {watcher.model_note && <p role="note">{watcher.model_note}</p>}
          {watcher.model_observations.length === 0 && !watcher.model_note ? (
            <p>No model observations for this snapshot. An empty watcher never lowers risk.</p>
          ) : (
            <ul>
              {watcher.model_observations.map((observation, index) => (
                <li key={`${String(observation.kind)}-${index}`}>
                  {formatWatcherValue(observation)} [{formatWatcherValue(observation.status)}
                  {observation.notice ? ` — ${formatWatcherValue(observation.notice)}` : ""}]
                </li>
              ))}
            </ul>
          )}
          {watcher.code_detections.length > 0 && (
            <>
              <h4>Code detections (independent of the model)</h4>
              <ul>
                {watcher.code_detections.map((detection, index) => (
                  <li key={`${formatWatcherValue(detection.kind ?? detection.rule)}-${index}`}>
                    {formatWatcherValue(detection.kind ?? detection.rule ?? "code detection")}:{" "}
                    {formatWatcherValue(detection.claim ?? detection.detail ?? "—")}
                  </li>
                ))}
              </ul>
            </>
          )}
          <p>
            Caregiver notice: {watcher.raise_caregiver_notice ? "raised" : "not raised"} (model or code
            detection; never lowered by an empty watcher).
          </p>
          {watcher.provenance && (
            <p>
              Model: {watcher.provenance.model_id} — route {watcher.provenance.provider_route}, recorded{" "}
              {watcher.provenance.recorded_at ?? "unknown"}, prompt{" "}
              {watcher.provenance.watcher_prompt_version}, input revision{" "}
              {watcher.provenance.input_revision}, laws {watcher.provenance.laws_version}.
            </p>
          )}
        </>
      )}
      </details>
      <details className="laws-details">
        <summary>Corrections</summary>
      {!corrections ? (
        <p role="status">Loading corrections…</p>
      ) : corrections.corrections.length === 0 ? (
        <p>No watcher corrections recorded yet.</p>
      ) : (
        <ul>
          {corrections.corrections.map((record: CorrectionRecord, index: number) => (
            <li key={`${record.scenario_id}-${record.evaluated_at_utc}-${index}`}>
              {record.scenario_id} at {record.evaluated_at_utc}: {formatWatcherValue(record.final_result)}. Original:{" "}
              {formatWatcherValue(record.original_claim)}. Failed checks: {formatWatcherValue(record.failed_checks)}.
              Revision: {formatWatcherValue(record.revision_claim)}. The ledger below is shown to the model as
              in-context examples only; the model itself is not retrained.
            </li>
          ))}
        </ul>
      )}
      </details>
    </section>
  );
}

const TRACE_SOURCE_COLORS: Record<string, string> = {
  calendar: "#0f766e",
  thermostat: "#c2410c",
  room_sensor: "#1d4ed8",
  electrical: "#a16207",
  weather: "#5b7fa6",
  human_report: "#92400e",
};

interface TraceMapNode {
  id: string;
  x: number;
  y: number;
  label: string;
  sub: string;
  color: string;
  state: string;
  detail: string;
}

interface TraceMapEdge {
  id: string;
  from: string;
  to: string;
  state: string;
  label: string;
  detail: string;
}

function traceNodeState(state: string): string {
  if (state === "pass") return "pass";
  if (state === "fail") return "fail";
  if (state === "quiet") return "quiet";
  return "stale";
}

function shortTraceLabel(label: string): string {
  return label.length > 30 ? `${label.slice(0, 29)}…` : label;
}

function buildTraceLayout(trace: TraceResponse): { nodes: TraceMapNode[]; edges: TraceMapEdge[]; height: number } {
  const colX = [10, 320, 630, 930];
  const nodeH = 48;
  const gap = 12;
  const nodes: TraceMapNode[] = [];
  const edges: TraceMapEdge[] = [];

  nodes.push({
    id: "pack",
    x: colX[0],
    y: 10,
    label: `evidence pack as of ${shortTimeLabel(trace.at)}`,
    sub: "only what was received by then",
    color: "#333333",
    state: "info",
    detail: trace.as_of_note,
  });
  trace.sources.forEach((source, index) => {
    const reading = source.latest_reading;
    nodes.push({
      id: `source-${source.source}`,
      x: colX[0],
      y: 10 + (index + 1) * (nodeH + gap),
      label: `${source.source}: ${source.availability}`,
      sub: source.freshness_reason,
      color: TRACE_SOURCE_COLORS[source.source] ?? "#444444",
      state: source.availability === "available" && source.freshness === "fresh" && !source.conflicted ? "pass" : source.freshness === "fresh" ? "fail" : "stale",
      detail: reading
        ? `reading ${reading.id}: ${String(reading.value)} ${reading.unit ?? ""} observed ${reading.observed_at}, received ${reading.received_at}; ${source.freshness_reason}${source.conflicted ? "; cited by contradictory readings" : ""}`
        : `${source.source}: ${source.freshness_reason}`,
    });
  });
  if (trace.human_report) {
    nodes.push({
      id: "human",
      x: colX[0],
      y: 10 + (trace.sources.length + 1) * (nodeH + gap),
      label: "human report, not a measurement",
      sub: "corroboration only",
      color: TRACE_SOURCE_COLORS.human_report ?? "#92400e",
      state: "stale",
      detail: `${String(trace.human_report.payload.transcript ?? "").slice(0, 300)} (${trace.human_report.note})`,
    });
  }

  trace.checks.forEach((check: TraceCheck, index: number) => {
    nodes.push({
      id: `check-${index}`,
      x: colX[1],
      y: 10 + index * (nodeH + gap),
      label: shortTraceLabel(`${check.check} · ${check.target}`),
      sub: check.passed === true ? "passed" : check.passed === false ? "failed" : "not run",
      color: "#444444",
      state: check.passed === true ? "pass" : check.passed === false ? "fail" : "stale",
      detail: check.reason,
    });
    const target = nodes.find((node) => node.id === `source-${check.target}`);
    edges.push({
      id: `edge-in-${index}`,
      from: target ? target.id : "pack",
      to: `check-${index}`,
      state: check.passed === true ? "pass" : check.passed === false ? "fail" : "stale",
      label: `${check.check} on ${check.target}`,
      detail: check.reason,
    });
  });

  const decisionCount = 2 + trace.watcher.code_detections.length + (trace.watcher.observations.length === 0 && trace.watcher.code_detections.length === 0 ? 1 : 0);
  const readinessState = trace.readiness.status === "on_track" || trace.readiness.status === "arrival_passed" ? "pass" : trace.readiness.status === "at_risk" ? "fail" : "stale";
  nodes.push({
    id: "readiness",
    x: colX[2],
    y: 10,
    label: `readiness: ${trace.readiness.status}`,
    sub: "computed by code",
    color: "#1a1a1a",
    state: readinessState,
    detail: trace.readiness.reasons.join("; ") || "no readiness reasons",
  });
  const stage = String(trace.verification.stage ?? "not available");
  nodes.push({
    id: "verification",
    x: colX[2],
    y: 10 + (nodeH + gap),
    label: `verification: ${shortTraceLabel(stage)}`,
    sub: "later readings only",
    color: "#1a1a1a",
    state: stage === "goal_verified" || stage === "arrival_met" ? "pass" : "stale",
    detail: Array.isArray(trace.verification.reasons) ? (trace.verification.reasons as string[]).join("; ") : String(trace.verification.reason ?? "verification not available"),
  });
  edges.push({ id: "edge-readiness-verification", from: "readiness", to: "verification", state: readinessState, label: "readiness into verification", detail: trace.readiness.reasons.join("; ") || "no readiness reasons" });
  trace.checks.forEach((_check: TraceCheck, index: number) => {
    edges.push({ id: `edge-check-decision-${index}`, from: `check-${index}`, to: "readiness", state: traceNodeState(nodes.find((node) => node.id === `check-${index}`)?.state ?? "stale"), label: "check into readiness", detail: trace.checks[index].reason });
  });
  trace.watcher.code_detections.forEach((detection, index: number) => {
    const record = detection as Record<string, string>;
    nodes.push({
      id: `detection-${index}`,
      x: colX[2],
      y: 10 + (index + 2) * (nodeH + gap),
      label: shortTraceLabel(`code: ${String(record.rule ?? record.kind ?? "detection")}`),
      sub: "independent of the model",
      color: "#444444",
      state: "fail",
      detail: String(record.detail ?? record.claim ?? ""),
    });
  });
  const watcherState = trace.watcher.status === "confirmed" ? "pass" : trace.watcher.status === "rejected" ? "fail" : "quiet";
  const watcherY = 10 + (2 + trace.watcher.code_detections.length) * (nodeH + gap);
  if (trace.watcher.observations.length === 0 && trace.watcher.code_detections.length === 0) {
    nodes.push({
      id: "no-detection",
      x: colX[2],
      y: watcherY,
      label: "no detection, never safe",
      sub: "absence is not an all-clear",
      color: "#d97706",
      state: "quiet",
      detail: "no model observation and no code detection at this time; absence of a detection is not an all-clear",
    });
  }
  nodes.push({
    id: "watcher",
    x: colX[2],
    y: watcherY + (trace.watcher.observations.length === 0 && trace.watcher.code_detections.length === 0 ? nodeH + gap : 0),
    label: `watcher (model): ${trace.watcher.status}`,
    sub: "AI noticed, code confirmed",
    color: "#7c3aed",
    state: watcherState,
    detail: trace.watcher.observations.length > 0
      ? trace.watcher.observations.map((obs) => `${String(obs.kind)}: ${String(obs.claim)} [${String(obs.status)}]`).join("; ")
      : (trace.watcher.model_note ?? "no model observations for this snapshot"),
  });
  if (trace.human_report) {
    edges.push({ id: "edge-human-verification", from: "human", to: "verification", state: "stale", label: "human report as corroboration only", detail: "a human report never counts as a sensor measurement" });
  }
  edges.push({ id: "edge-pack-watcher", from: "pack", to: "watcher", state: "info", label: "observations checked against the pack", detail: trace.watcher.model_note ?? "watcher observations verified against the evidence pack" });

  if (trace.permission) {
    const permission = trace.permission;
    const permissionState = permission.status === "approved" ? "pass" : permission.status === "declined" ? "fail" : "stale";
    const decidedAt = permission.decided_at ? formatTimestamp(permission.decided_at) : "an unknown time";
    const askedAt = permission.requested_at ? formatTimestamp(permission.requested_at) : "an unknown time";
    const permissionLabel =
      permission.status === "waiting"
        ? "No answer yet"
        : permission.status === "approved"
          ? `Approved by the caregiver at ${decidedAt}`
          : `Declined by the caregiver at ${decidedAt}`;
    const permissionEffect =
      permission.status === "waiting"
        ? "ARIA will not contact HVAC until she answers"
        : permission.status === "approved"
          ? "HVAC may now be contacted"
          : "No HVAC request; ARIA keeps monitoring";
    nodes.push({
      id: "permission",
      x: colX[3],
      y: 10 + trace.notices.length * (nodeH + gap),
      label: permissionLabel,
      sub: `${permissionEffect} — asked at ${askedAt}`,
      color: "#0e7490",
      state: permissionState,
      detail: `${permission.text} Asked at ${askedAt}. (${permission.note})`,
    });
    edges.push({ id: "edge-verification-permission", from: "verification", to: "permission", state: permissionState, label: "the caregiver is asked before HVAC is contacted", detail: permission.note });
  }

  trace.notices.forEach((notice, index: number) => {
    nodes.push({
      id: `notice-${index}`,
      x: colX[3],
      y: 10 + index * (nodeH + gap),
      label: `${notice.audience}: ${notice.allowed ? "raised" : "refused"}`,
      sub: notice.reason ?? `fields: ${notice.payload_keys.join(", ")}`,
      color: notice.allowed ? "#166534" : "#6b7280",
      state: notice.allowed ? "pass" : "stale",
      detail: notice.reason ?? `simulated payload fields: ${notice.payload_keys.join(", ")}`,
    });
    edges.push({ id: `edge-verification-notice-${index}`, from: "verification", to: `notice-${index}`, state: notice.allowed ? "pass" : "stale", label: `${notice.audience} notice ${notice.allowed ? "raised" : "refused"}`, detail: notice.reason ?? `simulated payload fields: ${notice.payload_keys.join(", ")}` });
    edges.push({ id: `edge-watcher-notice-${index}`, from: "watcher", to: `notice-${index}`, state: watcherState === "pass" ? "pass" : "quiet", label: "model and code detection into the notice", detail: trace.watcher.observations.length > 0 ? "a confirmed model observation supports the caregiver notice" : "no confirmed model observation; code detections decide" });
  });

  const counts = [trace.sources.length + 2, trace.checks.length, decisionCount + 1, trace.notices.length + (trace.permission ? 1 : 0)];
  const height = Math.max(...counts) * (nodeH + gap) + 20;
  return { nodes, edges, height: Math.max(height, 220) };
}

function traceEdgePath(nodes: TraceMapNode[], from: string, to: string): string {
  const start = nodes.find((node) => node.id === from);
  const end = nodes.find((node) => node.id === to);
  if (!start || !end) return "";
  const x1 = start.x + 250;
  const y1 = start.y + 24;
  const x2 = end.x;
  const y2 = end.y + 24;
  const mid = Math.max(30, (x2 - x1) / 2);
  return `M ${x1} ${y1} C ${x1 + mid} ${y1}, ${x2 - mid} ${y2}, ${x2} ${y2}`;
}

function TraceView({ scenario, at, times, onSelectAt, onBack, active, investigationId }: { scenario: string; at: string; times: Array<{ label: string; at: string }>; onSelectAt: (at: string) => void; onBack: () => void; active: boolean; investigationId: string | null }) {
  const [trace, setTrace] = useState<TraceResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<{ title: string; state: string; detail: string } | null>(null);

  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    setError(null);
    setTrace(null);
    setSelected(null);
    fetchTrace(scenario, at, investigationId)
      .then((response) => {
        if (cancelled) return;
        if (Date.parse(response.at) !== Date.parse(at)) return;
        setTrace(response);
      })
      .catch(() => {
        if (!cancelled) setError("ARIA's view is not reachable");
      });
    return () => {
      cancelled = true;
    };
  }, [scenario, at, active, investigationId]);

  const layout = trace ? buildTraceLayout(trace) : null;

  return (
    <section aria-labelledby="trace-heading">
      <h2 id="trace-heading">ARIA&rsquo;s view</h2>
      <details className="trace-about-details">
        <summary>About this map</summary>
        <p>
          A live map of how each decision is made at this replay moment, drawn only from the trace: sources on the
          left, code checks next, the code-computed decision, then notices. Violet is the model (watcher); everything
          else is code. Only evidence received by this time is shown.
        </p>
        <ul className="trace-legend" aria-label="Map legend">
          <li><span className="trace-swatch trace-swatch-pass" /> passing streak glows</li>
          <li><span className="trace-swatch trace-swatch-stale" /> stale or quiet, grey dashed</li>
          <li><span className="trace-swatch trace-swatch-fail" /> failed check stops here</li>
          <li><span className="trace-swatch trace-swatch-model" /> violet is the model, the rest is code</li>
          <li><span className="trace-swatch trace-swatch-quiet" /> no detection, never safe</li>
          <li><span className="trace-swatch trace-swatch-permission" /> teal is the caregiver&rsquo;s permission</li>
        </ul>
      </details>
      {!investigationId && (
        <p>Showing the recorded story; your own choices appear once you start an investigation.</p>
      )}
      <button type="button" className="ghost-button" onClick={onBack}>
        Back
      </button>
      <div className="trace-times" role="group" aria-label="Trace replay time">
        {times.map((time) => (
          <button
            key={time.at}
            type="button"
            className="ghost-button"
            onClick={() => onSelectAt(time.at)}
            aria-pressed={at === time.at}
            aria-label={`Trace at ${time.label}`}
          >
            {time.label}
          </button>
        ))}
      </div>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {!trace ? (
        <p role="status">Loading ARIA&rsquo;s view…</p>
      ) : (
        <>
          <div className="trace-map-wrap">
            <svg data-testid="trace-map" viewBox={`0 0 1200 ${layout?.height ?? 220}`} role="img" aria-label={`ARIA's view map at ${at}`}>
              {layout?.edges.map((edge) => (
                <g key={edge.id}>
                  <path
                    d={traceEdgePath(layout.nodes, edge.from, edge.to)}
                    className={`trace-streak trace-streak-${traceNodeState(edge.state)}`}
                    data-state={traceNodeState(edge.state)}
                    data-testid={`trace-streak-${edge.id}`}
                  />
                  <path
                    d={traceEdgePath(layout.nodes, edge.from, edge.to)}
                    className="trace-streak-hit"
                    data-state={traceNodeState(edge.state)}
                    onClick={() => setSelected({ title: edge.label, state: edge.state, detail: edge.detail })}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") setSelected({ title: edge.label, state: edge.state, detail: edge.detail });
                    }}
                    tabIndex={0}
                    role="button"
                    aria-label={`${edge.label}: ${edge.detail}`}
                  >
                    <title>{`${edge.label}: ${edge.detail}`}</title>
                  </path>
                </g>
              ))}
              {layout?.nodes.map((node) => (
                <g
                  key={node.id}
                  className={`trace-node trace-node-${traceNodeState(node.state)}`}
                  data-state={traceNodeState(node.state)}
                  data-testid={`trace-node-${node.id}`}
                  onClick={() => setSelected({ title: node.label, state: node.state, detail: `${node.sub} — ${node.detail}` })}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") setSelected({ title: node.label, state: node.state, detail: `${node.sub} — ${node.detail}` });
                  }}
                  tabIndex={0}
                  role="button"
                  aria-label={`${node.label}: ${node.sub}`}
                >
                  <title>{`${node.label}: ${node.sub}`}</title>
                  <rect x={node.x} y={node.y} width={node.id === "pack" ? 250 : node.x >= 930 ? 230 : node.x >= 630 ? 230 : 250} height={48} rx={8} style={{ stroke: node.color }} />
                  <text x={node.x + 12} y={node.y + 20}>{shortTraceLabel(node.label)}</text>
                  <text x={node.x + 12} y={node.y + 38} className="trace-node-sub">{shortTraceLabel(node.sub)}</text>
                </g>
              ))}
            </svg>
          </div>
          <div data-testid="trace-detail" className="trace-detail" role="status">
            {selected ? (
              <>
                <h3>{selected.title}</h3>
                <p>State: {selected.state}</p>
                <p>{selected.detail}</p>
              </>
            ) : (
              <p>Select a node or streak to see the reading, check, or result.</p>
            )}
          </div>
          <details className="trace-steps-details">
            <summary>Show all {trace.steps.length} steps</summary>
            <ol className="trace-steps">
              {trace.steps.map((step) => (
              <li
                key={step.seq}
                data-state={traceNodeState(step.state)}
                data-testid={`trace-step-${step.seq}`}
                onClick={() => setSelected({ title: step.label, state: step.state, detail: step.detail })}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") setSelected({ title: step.label, state: step.state, detail: step.detail });
                }}
                tabIndex={0}
                role="button"
                aria-label={`${step.label}: ${step.detail}`}
              >
                <span className={`trace-dot trace-dot-${traceNodeState(step.state)}`} aria-hidden="true" />
                {step.label} — {step.detail}
              </li>
            ))}
            </ol>
          </details>
        </>
      )}
    </section>
  );
}

function shortTimeLabel(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return `${new Intl.DateTimeFormat("en-US", {
    timeZone: PROPERTY_TIMEZONE,
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  }).format(date)} ET`;
}

function VersionLine({ commit }: { commit: string | null }) {
  if (commit === null) return null;
  const short = commit === "unknown" ? "unknown" : commit.slice(0, 7);
  return (
    <p className="version-line" data-testid="version-line">
      Version {short}
    </p>
  );
}

type HousePage = "house" | "reasoning" | "integrations";

const PAGE_LABEL: Record<HousePage, string> = {
  house: "House",
  reasoning: "Reasoning",
  integrations: "Integrations",
};

type StatusTone = "ok" | "watch" | "risk" | "unknown";

function formatLongTime(value: string | null): string {
  if (!value) return "No replay time";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const weekday = new Intl.DateTimeFormat("en-US", { timeZone: PROPERTY_TIMEZONE, weekday: "long" }).format(date);
  const day = new Intl.DateTimeFormat("en-US", { timeZone: PROPERTY_TIMEZONE, day: "numeric" }).format(date);
  const month = new Intl.DateTimeFormat("en-US", { timeZone: PROPERTY_TIMEZONE, month: "long" }).format(date);
  const time = new Intl.DateTimeFormat("en-US", {
    timeZone: PROPERTY_TIMEZONE,
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  }).format(date);
  return `${weekday} ${day} ${month}, ${time}, ET`;
}

interface Verdict {
  headline: string;
  tone: StatusTone;
}

function buildVerdict(
  readiness: ReadinessResult | null,
  verification: VerificationResult | null,
  targetTemp: number | null,
  targetUnit: string | null,
): Verdict | null {
  if (!readiness && !verification) return null;
  if (verification?.stage === "arrival_met") {
    return { headline: "The house was warm by 7:00 — the expectation was met.", tone: "ok" };
  }
  if (verification?.stage === "goal_verified") {
    const goal = targetTemp !== null ? `${formatTargetTemp(targetTemp)} ${targetUnit ?? "F"}` : "its goal";
    return { headline: `The house reached ${goal} and held it — the goal is verified.`, tone: "ok" };
  }
  if (readiness?.status === "on_track") {
    return { headline: "The house is on track to be warm by 7:00.", tone: "ok" };
  }
  if (readiness?.status === "at_risk") {
    return { headline: "The house is cooling. It may not be warm by 7:00.", tone: "risk" };
  }
  if (readiness?.status === "arrival_passed") {
    return { headline: "The warm-by time has passed.", tone: "watch" };
  }
  return { headline: "ARIA can't tell yet.", tone: "unknown" };
}

function availabilityTone(availability: Availability): StatusTone {
  if (availability === "available") return "ok";
  if (availability === "stale") return "watch";
  if (availability === "invalid" || availability === "conflicting") return "risk";
  return "unknown";
}

function sourceByKind(sources: SourceStatus[] | undefined, kind: SourceKind): SourceStatus | null {
  return sources?.find((status) => status.source === kind) ?? null;
}

function buildLead(
  sources: SourceStatus[] | undefined,
  trend: IndoorTrend | null,
): string | null {
  const parts: string[] = [];
  const room = sourceByKind(sources, "room_sensor");
  if (room && room.newest_value !== null && room.newest_value !== undefined) {
    const unit = room.newest_unit ? ` ${room.newest_unit}` : "";
    let roomPart = `Living room ${room.newest_value}${unit}`;
    const rate = trend?.rate_per_hour;
    if (typeof rate === "number" && trend?.sufficient) {
      if (rate < 0) roomPart += ` and falling ${Math.abs(Math.round(rate * 10) / 10)} F an hour`;
      else if (rate > 0) roomPart += ` and rising ${Math.round(rate * 10) / 10} F an hour`;
    }
    parts.push(roomPart);
  }
  const thermostat = sourceByKind(sources, "thermostat");
  if (thermostat && thermostat.availability !== "available") {
    parts.push(
      thermostat.newest_observed_at
        ? `the thermostat has been silent since ${shortTimeLabel(thermostat.newest_observed_at)}`
        : "the thermostat is not reporting",
    );
  }
  if (parts.length === 0) return null;
  return `${parts.join("; ")}.`;
}

function gapCalloutFor(sources: SourceStatus[] | undefined): string | null {
  const thermostat = sourceByKind(sources, "thermostat");
  if (thermostat && thermostat.availability !== "available") {
    return thermostat.newest_observed_at
      ? `Thermostat not reporting since ${shortTimeLabel(thermostat.newest_observed_at)}`
      : "Thermostat not reporting";
  }
  const room = sourceByKind(sources, "room_sensor");
  if (room && room.availability !== "available") {
    return "Room sensor not reporting";
  }
  return null;
}

function CameraTile({ scenario, at, enabled }: { scenario: string; at: string; enabled: boolean }) {
  const [visual, setVisual] = useState<VisualEvidence | null | undefined>(undefined);

  useEffect(() => {
    if (!enabled) {
      setVisual(null);
      return;
    }
    let live = true;
    setVisual(undefined);
    fetchVisual(scenario, at)
      .then((response) => {
        if (!live || response.scenario !== scenario) return;
        setVisual(response.visual);
      })
      .catch(() => {
        if (live) setVisual(null);
      });
    return () => {
      live = false;
    };
  }, [scenario, at, enabled]);

  if (visual === undefined) {
    return (
      <>
        <p className="tile-value">Loading camera…</p>
        <p className="tile-sub">synthetic frame</p>
      </>
    );
  }
  if (visual === null) {
    return (
      <>
        <p className="tile-value">No frame</p>
        <p className="tile-sub">no synthetic frame at this time</p>
      </>
    );
  }
  return (
    <>
      <p className="tile-value">{visual.object_count === 0 ? "Nothing found" : `${visual.object_count} found`}</p>
      <p className="tile-sub">
        {visual.caption}
        {visual.object_count === 0 ? " — no detection is not an all-clear." : ""}
      </p>
    </>
  );
}

function GlanceTiles({
  sources,
  trend,
  targetTemp,
  targetUnit,
  plannedArrival,
  verdictTone,
  scenario,
  at,
  visualEnabled,
}: {
  sources: SourceStatus[] | undefined;
  trend: IndoorTrend | null;
  targetTemp: number | null;
  targetUnit: string | null;
  plannedArrival: string | null;
  verdictTone: StatusTone;
  scenario: string;
  at: string;
  visualEnabled: boolean;
}) {
  const room = sourceByKind(sources, "room_sensor");
  const thermostat = sourceByKind(sources, "thermostat");
  const insideValue =
    room && room.newest_value !== null && room.newest_value !== undefined
      ? `${room.newest_value}${room.newest_unit ? ` ${room.newest_unit}` : ""}`
      : "No reading";
  const rate = trend?.rate_per_hour;
  const insideTrend =
    typeof rate === "number" && trend?.sufficient
      ? rate < 0
        ? "falling"
        : rate > 0
          ? "rising"
          : "steady"
      : "trend unknown";
  const targetLabel = targetTemp !== null ? `${formatTargetTemp(targetTemp)} ${targetUnit ?? "F"}` : "the goal";
  const arrivalLabel = plannedArrival ? shortTimeLabel(plannedArrival) : "the warm-by time";
  const thermostatState =
    !thermostat || thermostat.availability === "available"
      ? { word: "Reporting", tone: "ok" as StatusTone, sub: "thermostat" }
      : {
          word: "Silent",
          tone: "risk" as StatusTone,
          sub: thermostat.newest_observed_at
            ? `thermostat, silent since ${shortTimeLabel(thermostat.newest_observed_at)}`
            : "thermostat",
        };
  return (
    <section aria-labelledby="house-now-heading">
      <h2 id="house-now-heading">The house right now</h2>
      <ul className="tiles">
        <li className="tile">
          <p className="tile-title">
            <span className={`status-dot status-dot-${room ? availabilityTone(room.availability) : "unknown"}`} aria-hidden="true" />
            Inside
          </p>
          <p className="tile-value">{insideValue}</p>
          <p className="tile-sub">
            room sensor · {insideTrend}
          </p>
        </li>
        <li className="tile">
          <p className="tile-title">
            <span className={`status-dot status-dot-${verdictTone}`} aria-hidden="true" />
            Warm-by
          </p>
          <p className="tile-value">
            {targetLabel} by {arrivalLabel}
          </p>
          <p className="tile-sub">warm-by expectation</p>
        </li>
        <li className="tile">
          <p className="tile-title">
            <span className={`status-dot status-dot-${thermostatState.tone}`} aria-hidden="true" />
            Furnace and thermostat
          </p>
          <p className="tile-value">{thermostatState.word}</p>
          <p className="tile-sub">{thermostatState.sub}</p>
        </li>
        <li className="tile">
          <p className="tile-title">
            <span className="status-dot status-dot-unknown" aria-hidden="true" />
            Camera
          </p>
          <CameraTile scenario={scenario} at={at} enabled={visualEnabled} />
        </li>
      </ul>
    </section>
  );
}

function NoticeArticle({
  notification,
  onAck,
  ackingId,
  whatsappConfigured,
  onSendWhatsapp,
  sendingWhatsappId,
}: {
  notification: Notification;
  onAck: (notification: Notification) => void;
  ackingId: string | null;
  whatsappConfigured: boolean;
  onSendWhatsapp: (notification: Notification) => void;
  sendingWhatsappId: string | null;
}) {
  const audienceLabel =
    NOTIFICATION_AUDIENCE_LABEL[notification.audience] ?? notification.audience;
  const acks = notification.acks ?? [];
  const ack = acks.length > 0 ? acks[acks.length - 1] : null;
  return (
    <article
      className="notification-card"
      aria-label={notification.kind.startsWith("caregiver_update_") ? `${audienceLabel} update` : `${audienceLabel} notification`}
    >
      <h3 className="card-title">{audienceLabel}</h3>
      <p className="notification-state">{notificationStateInWords(notification)}</p>
      <p>
        Created:{" "}
        <time dateTime={notification.created_at}>
          {formatTimestamp(notification.created_at)}
        </time>
      </p>
      <p>
        {whatsappLine(notification.whatsapp)}
      </p>
      <details className="notice-message-details">
        <summary>Show the simulated message</summary>
        <h4 className="notice-facts-heading">Facts when this notice was created ({shortTimeLabel(notification.created_at)})</h4>
        <PayloadFacts payload={notification.payload} />
      </details>
      {notification.audience === "hvac_company" &&
        notification.state === "simulated_delivered" &&
        whatsappConfigured && (
          <button
            type="button"
            className="ghost-button"
            onClick={() => onSendWhatsapp(notification)}
            disabled={sendingWhatsappId === notification.id}
          >
            Send to my test phone (WhatsApp)
          </button>
        )}
      {ack ? (
        <p className="notification-ack">
          Acknowledged, not resolved —{" "}
          <time dateTime={ack.acknowledged_at}>{formatTimestamp(ack.acknowledged_at)}</time>
        </p>
      ) : (notification.audience === "property_manager" ||
          notification.audience === "family_caregiver") &&
        !notification.kind.startsWith("caregiver_update_") &&
        notification.state === "simulated_delivered" ? (
        <button
          type="button"
          className="ghost-button"
          onClick={() => onAck(notification)}
          disabled={ackingId === notification.id}
        >
          Acknowledge (simulated)
        </button>
      ) : null}
    </article>
  );
}

function KnowRow({
  tone,
  title,
  meta,
  children,
}: {
  tone: StatusTone;
  title: string;
  meta: string;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(true);
  return (
    <li className="know-row" data-testid={`know-row-${title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}>
      <span className={`status-dot status-dot-${tone}`} aria-hidden="true" />
      <div className="know-row-body">
        <button
          type="button"
          className="know-row-toggle"
          aria-expanded={open}
          onClick={() => setOpen((value) => !value)}
        >
          <span className="know-row-title">{title}</span>
          <span className="know-row-meta">{meta}</span>
        </button>
        {open && <div className="know-row-detail">{children}</div>}
      </div>
    </li>
  );
}

function WhoKnows({
  permission,
  onDecide,
  deciding,
  whatsappConfigured,
  onSendWhatsapp,
  sending,
  notifications,
  notificationsError,
  onAck,
  ackingId,
  onSendWhatsappFor,
  sendingWhatsappId,
  homeownerReady,
  sectionClassName,
}: {
  permission: CaregiverPermission | null;
  onDecide: (decision: "approve" | "decline") => void;
  deciding: boolean;
  whatsappConfigured: boolean;
  onSendWhatsapp: () => void;
  sending: boolean;
  notifications: Notification[];
  notificationsError: string | null;
  onAck: (notification: Notification) => void;
  ackingId: string | null;
  onSendWhatsappFor: (notification: Notification) => void;
  sendingWhatsappId: string | null;
  homeownerReady: boolean;
  sectionClassName?: string;
}) {
  const caregiverNotices = notifications.filter((item) => item.audience === "family_caregiver");
  const hvacNotices = notifications.filter((item) => item.audience === "hvac_company");
  const homeownerNotices = notifications.filter((item) => item.audience === "homeowner");
  const managerNotices = notifications.filter((item) => item.audience === "property_manager");
  const articleProps = { onAck, ackingId, whatsappConfigured, onSendWhatsapp: onSendWhatsappFor, sendingWhatsappId };
  const caregiverClause = permission
    ? `${caregiverStatusCopy(permission).headline} ${caregiverStatusCopy(permission).effect}`
    : "No caregiver request at this step — no HVAC decision to make.";
  return (
    <section aria-labelledby="who-knows-heading" className={sectionClassName}>
      <p className="section-label">Notices</p>
      <h2 id="who-knows-heading">Who knows</h2>
      {notificationsError && (
        <p role="alert" className="error">
          Notifications not reachable
        </p>
      )}
      {!permission && notifications.length === 0 && !notificationsError ? (
        <p>No notices visible at this step.</p>
      ) : (
      <ul className="know-rows">
        {permission && (
          <KnowRow
            tone={permission.status === "approved" ? "ok" : permission.status === "declined" ? "risk" : "watch"}
            title="Family caregiver"
            meta={caregiverStatusCopy(permission).headline}
          >
            <CaregiverPermissionCard
              permission={permission}
              onDecide={onDecide}
              deciding={deciding}
              whatsappConfigured={whatsappConfigured}
              onSendWhatsapp={onSendWhatsapp}
              sending={sending}
            />
            {caregiverNotices.map((notification) => (
              <NoticeArticle key={notification.id} notification={notification} {...articleProps} />
            ))}
          </KnowRow>
        )}
        {(hvacNotices.length > 0 || !permission) && (
          <KnowRow
            tone={
              hvacNotices.some((item) => item.state === "simulated_delivered")
                ? "ok"
                : hvacNotices.some((item) => item.state === "refused")
                  ? "risk"
                  : "unknown"
            }
            title="HVAC company"
            meta={
              hvacNotices.some((item) => item.state === "simulated_delivered")
                ? `Simulated request sent — fields sent: ${Object.keys(
                  hvacNotices.find((item) => item.state === "simulated_delivered")?.payload ?? {},
                ).join(", ")}. ${caregiverClause}`
                : hvacNotices.length > 0
                  ? `No request sent: ${refusalReasonInWords(hvacNotices[0])}. ${caregiverClause}`
                  : `No HVAC request at this time. ${caregiverClause}`
            }
          >
            <p>{caregiverClause}</p>
            {hvacNotices.length === 0 ? (
              <p>No HVAC request at this time.</p>
            ) : (
              hvacNotices.map((notification) => (
                <NoticeArticle key={notification.id} notification={notification} {...articleProps} />
              ))
            )}
          </KnowRow>
        )}
        <KnowRow
          tone={homeownerReady ? "ok" : "unknown"}
          title="Resident and homeowner update"
          meta={
            homeownerReady
              ? "Warm-by expectation met — see the homeowner update below."
              : "No homeowner update at this step."
          }
        >
          {homeownerNotices.length === 0 ? (
            <p>No homeowner update at this step.</p>
          ) : (
            homeownerNotices.map((notification) => (
              <NoticeArticle key={notification.id} notification={notification} {...articleProps} />
            ))
          )}
        </KnowRow>
        {managerNotices.map((notification) => (
          <KnowRow key={notification.id} tone="unknown" title="Property manager" meta={notificationStateInWords(notification)}>
            <NoticeArticle notification={notification} {...articleProps} />
          </KnowRow>
        ))}
      </ul>
      )}
    </section>
  );
}

function CodeChecks({ scenario, at, active }: { scenario: string; at: string; active: boolean }) {
  const [trace, setTrace] = useState<TraceResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    setError(null);
    setTrace(null);
    fetchTrace(scenario, at)
      .then((response) => {
        if (cancelled) return;
        if (Date.parse(response.at) !== Date.parse(at)) return;
        setTrace(response);
      })
      .catch(() => {
        if (!cancelled) setError("Code checks are not reachable");
      });
    return () => {
      cancelled = true;
    };
  }, [scenario, at, active]);

  return (
    <section aria-labelledby="code-checks-heading">
      {!(trace && trace.checks.length > 0) && (
        <>
          <p className="section-label">Code checks</p>
          <h2 id="code-checks-heading">Freshness, conflicts, units and Laws</h2>
        </>
      )}
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {!trace && !error && <p role="status">Loading code checks…</p>}
      {trace && trace.checks.length === 0 && <p>No code checks ran at this time.</p>}
      {trace && trace.checks.length > 0 && (
        <details className="checks-details">
          <summary>Show all {trace.checks.length} checks</summary>
          <h2 id="code-checks-heading">Freshness, conflicts, units and Laws</h2>
          <p className="checks-summary" role="status">
            {trace.checks.length} checks: {trace.checks.filter((check) => check.passed === true).length}{" "}
            passed, {trace.checks.filter((check) => check.passed === false).length} failed,{" "}
            {trace.checks.filter((check) => check.passed !== true && check.passed !== false).length} not
            run
          </p>
          <details className="checks-details">
            <summary>
              Failed ({trace.checks.filter((check) => check.passed === false).length})
            </summary>
            <ul className="know-rows">
              {trace.checks
                .filter((check) => check.passed === false)
                .map((check, index) => (
                  <li key={`${check.check}-${check.target}-${index}`} className="know-row">
                    <span className="status-dot status-dot-risk" aria-hidden="true" />
                    <div className="know-row-body">
                      <p className="know-row-title">
                        {check.check} on {check.target} — failed
                      </p>
                      <p className="know-row-meta">{check.reason}</p>
                    </div>
                  </li>
                ))}
            </ul>
          </details>
          {trace.checks.some((check) => check.passed === true) && (
            <details className="checks-details">
              <summary>
                Passed ({trace.checks.filter((check) => check.passed === true).length})
              </summary>
              <ul className="know-rows">
                {trace.checks
                  .filter((check) => check.passed === true)
                  .map((check, index) => (
                    <li key={`${check.check}-${check.target}-${index}`} className="know-row">
                      <span className="status-dot status-dot-ok" aria-hidden="true" />
                      <div className="know-row-body">
                        <p className="know-row-title">
                          {check.check} on {check.target} — passed
                        </p>
                        <p className="know-row-meta">{check.reason}</p>
                      </div>
                    </li>
                  ))}
              </ul>
            </details>
          )}
          {trace.checks.some((check) => check.passed !== true && check.passed !== false) && (
            <details className="checks-details">
              <summary>
                Not run ({trace.checks.filter((check) => check.passed !== true && check.passed !== false).length})
              </summary>
              <ul className="know-rows">
                {trace.checks
                  .filter((check) => check.passed !== true && check.passed !== false)
                  .map((check, index) => (
                    <li key={`${check.check}-${check.target}-${index}`} className="know-row">
                      <span className="status-dot status-dot-unknown" aria-hidden="true" />
                      <div className="know-row-body">
                        <p className="know-row-title">
                          {check.check} on {check.target} — not run
                        </p>
                        <p className="know-row-meta">{check.reason}</p>
                      </div>
                    </li>
                  ))}
              </ul>
            </details>
          )}
        </details>
      )}
    </section>
  );
}

function AppHeader({
  page,
  onPage,
  showNav,
  pillText,
  pillTone,
  times,
  selectedAt,
  onStep,
  canStep,
  theme,
  onToggleTheme,
}: {
  page: HousePage;
  onPage: (next: HousePage) => void;
  showNav: boolean;
  pillText: string;
  pillTone: StatusTone;
  times: Array<{ label: string; at: string }>;
  selectedAt: string;
  onStep: (at: string) => void;
  canStep: boolean;
  theme: "light" | "dark";
  onToggleTheme: () => void;
}) {
  const index = times.findIndex((time) => Date.parse(time.at) === Date.parse(selectedAt));
  const canBack = canStep && index > 0;
  const canNext = canStep && index >= 0 && index < times.length - 1;
  return (
    <>
      <header className="site-header">
        <div className="site-header-left">
          <span className="wordmark">ARIA Home</span>
          {showNav && (
            <nav className="tabs" aria-label="Pages">
              {(Object.keys(PAGE_LABEL) as HousePage[]).map((key) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => onPage(key)}
                  aria-current={page === key ? "page" : undefined}
                >
                  {PAGE_LABEL[key]}
                </button>
              ))}
            </nav>
          )}
        </div>
        <div className="site-header-right">
          <p className="status-pill">
            <span className={`status-dot status-dot-${pillTone}`} aria-hidden="true" />
            {pillText}
          </p>
          {showNav && (
            <div className="stepper" role="group" aria-label="Replay time">
              <button
                type="button"
                onClick={() => index > 0 && onStep(times[index - 1].at)}
                disabled={!canBack}
                aria-label="Go back one replay step"
              >
                Back
              </button>
              <span className="eval-time" role="status">
                {shortTimeLabel(selectedAt)}
              </span>
              <button
                type="button"
                onClick={() => index >= 0 && index < times.length - 1 && onStep(times[index + 1].at)}
                disabled={!canNext}
                aria-label="Go forward one replay step"
              >
                Next
              </button>
            </div>
          )}
          <button
            type="button"
            className="theme-toggle"
            onClick={onToggleTheme}
            aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          >
            {theme === "dark" ? "Light" : "Dark"}
          </button>
        </div>
      </header>
      <p className="disclosure-strip">{PUBLIC_DISCLOSURE}</p>
    </>
  );
}

export default function App() {
  // Test-only inset zoom: ?inset=<panel> hides all but that panel and scales it (see index.css). No effect without the parameter.
  const inset =
    typeof window !== "undefined" ? new URLSearchParams(window.location.search).get("inset") : null;
  const keyName =
    typeof window !== "undefined" ? new URLSearchParams(window.location.search).get("key") : null;
  const keyCaption = keyName ? KEY_CAPTIONS[keyName] : undefined;
  const insetPanels = inset ? (INSET_TARGETS[inset] ?? []) : [];
  const insetClass = (panel: string) => (insetPanels.includes(panel) ? "inset-target" : undefined);
  const [data, setData] = useState<SourcesResponse | null>(null);
  const [contextData, setContextData] = useState<ContextResponse | null>(null);
  const [contextError, setContextError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [createdInvestigation, setCreatedInvestigation] =
    useState<CreateInvestigationResponse | null>(null);
  const [investigationError] = useState<string | null>(null);
  const [scenario, setScenario] = useState<string>(SCENARIOS[0].id);
  const [investigationId, setInvestigationId] = useState<string | null>(null);
  const [outcome, setOutcome] = useState<OutcomeResult | null>(null);
  const [history, setHistory] = useState<OutcomeHistoryEntry[]>([]);
  const [followUpUnit, setFollowUpUnit] = useState<string | null>(null);
  const [replayAt, setReplayAt] = useState<string | null>(null);
  const [replayLoading, setReplayLoading] = useState(false);
  const [replayError, setReplayError] = useState<string | null>(null);
  const [verification, setVerification] = useState<VerificationResult | null>(null);
  const [evidenceTimeline, setEvidenceTimeline] = useState<EvidenceTimelineEntry[]>([]);
  const [humanReport, setHumanReport] = useState<HumanReportPayload | null>(null);
  const [verificationHistory, setVerificationHistory] = useState<VerificationHistoryEntry[]>([]);
  const [events, setEvents] = useState<ScenarioEvent[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [notificationsError, setNotificationsError] = useState<string | null>(null);
  const [ackingId, setAckingId] = useState<string | null>(null);
  const [whatsappConfigured, setWhatsappConfigured] = useState(false);
  const [sendingWhatsappId, setSendingWhatsappId] = useState<string | null>(null);
  const [followUpTargetTemp, setFollowUpTargetTemp] = useState<number | null>(null);
  const [selectedAt, setSelectedAt] = useState<string>(REPLAY_START_AT);
  const [livePower, setLivePower] = useState<LivePowerResponse | null>(null);
  const [cameraConfigured, setCameraConfigured] = useState(false);
  const [sourcesLoading, setSourcesLoading] = useState(false);
  const [publicMode, setPublicMode] = useState<boolean | null>(null);
  const [caregiverPermission, setCaregiverPermission] = useState<CaregiverPermission | null>(null);
  const [replayMetrics, setReplayMetrics] = useState<ReplayMetrics | null>(null);
  const [recordedReplay, setRecordedReplay] = useState<RecordedInvestigation | null>(null);
  const [recordedByAt, setRecordedByAt] = useState<Record<string, RecordedInvestigation>>({});
  const [decidingPermission, setDecidingPermission] = useState(false);
  const [version, setVersion] = useState<string | null>(null);
  const [storyCheckpoints, setStoryCheckpoints] = useState<string[]>([]);
  const [view, setView] = useState<"landing" | "story" | "free" | "laws" | "trace" | null>(null);
  const [page, setPage] = useState<HousePage>("house");
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    try {
      const stored = window.localStorage.getItem("aria-home-theme");
      if (stored === "light" || stored === "dark") return stored;
    } catch {
      // storage unavailable; fall through to the OS preference
    }
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  });
  const [storyIndex, setStoryIndex] = useState(0);
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const [lawsOpen, setLawsOpen] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [resetError, setResetError] = useState<string | null>(null);
  const sourcesTokenRef = useRef(0);
  const contextTokenRef = useRef(0);
  const investigationTokenRef = useRef(0);
  const replayTokenRef = useRef(0);
  const eventsTokenRef = useRef(0);
  const noFollowUpIds = useRef<Set<string>>(new Set());
  const createdAtRef = useRef<string | null>(null);

  useEffect(() => {
    let live = true;
    fetchHealth()
      .then((health) => {
        if (!live) return;
        setVersion(health.version?.commit ?? "unknown");
        if (health.public_demo !== true) {
          setPublicMode(false);
          setView((current) => current ?? "free");
          return;
        }
        return fetchScenarios().then((response) => {
          if (!live) return;
          const scenarios = response && Array.isArray(response.scenarios) ? response.scenarios : [];
          const story = scenarios.find((item) => item.id === STORY_SCENARIO);
          setPublicMode(true);
          setStoryCheckpoints(
            story && Array.isArray(story.checkpoints) ? [...story.checkpoints] : [],
          );
          setView((current) => current ?? "landing");
        });
      })
      .catch(() => {
        if (!live) return;
        setPublicMode(false);
        setView((current) => current ?? "free");
      });
    return () => {
      live = false;
    };
  }, []);

  useEffect(() => {
    if (publicMode !== true) return;
    if (scenario !== STORY_SCENARIO || storyCheckpoints.length === 0) return;
    setStoryIndex((current) => Math.min(current, storyCheckpoints.length - 1));
    if (!storyCheckpoints.includes(selectedAt)) setSelectedAt(storyCheckpoints[0]);
  }, [publicMode, scenario, storyCheckpoints, selectedAt]);

  useEffect(() => {
    if (publicMode !== false && scenario === STORY_SCENARIO && !storyCheckpoints.includes(selectedAt)) return;
    const token = ++sourcesTokenRef.current;
    setSourcesLoading(true);
    setError(null);
    fetchSources(scenario, selectedAt)
      .then((response) => {
        if (token !== sourcesTokenRef.current) return;
        if (response.scenario !== scenario) return;
        if (Date.parse(response.at) !== Date.parse(selectedAt)) return;
        setData(response);
        setSourcesLoading(false);
      })
      .catch(() => {
        if (token !== sourcesTokenRef.current) return;
        setError("Backend not reachable");
        setSourcesLoading(false);
      });
  }, [scenario, selectedAt, publicMode, storyCheckpoints]);

  useEffect(() => {
    if (publicMode !== false && scenario === STORY_SCENARIO && !storyCheckpoints.includes(selectedAt)) return;
    const token = ++contextTokenRef.current;
    setContextError(null);
    fetchContext(scenario, selectedAt)
      .then((response) => {
        if (token !== contextTokenRef.current) return;
        if (response.scenario !== scenario) return;
        if (Date.parse(response.at) !== Date.parse(selectedAt)) return;
        setContextData(response);
      })
      .catch(() => {
        if (token !== contextTokenRef.current) return;
        setContextError("Confirmed plan not reachable");
      });
  }, [scenario, selectedAt, publicMode, storyCheckpoints]);

  useEffect(() => {
    if (publicMode === null) return;
    const token = ++investigationTokenRef.current;
    const controller = new AbortController();
    const search = new URLSearchParams(window.location.search);
    const publicStart =
      publicMode === true && scenario === STORY_SCENARIO && storyCheckpoints.length > 0
        ? storyCheckpoints[0]
        : null;
    const startAt = search.get("e2e_at") ?? publicStart ?? startAtForScenario(scenario);
    const e2eParts: string[] = [];
    for (const [from, to] of [["e2e_delay_s", "test_delay_s"], ["e2e_lease_s", "lease_s"]] as const) {
      const value = search.get(from);
      if (value !== null) e2eParts.push(`${to}=${encodeURIComponent(value)}`);
    }
    if (search.get("e2e_fail") !== null) e2eParts.push(`test_fail=${encodeURIComponent(search.get("e2e_fail") ?? "1")}`);
    const queryExtra = e2eParts.length ? e2eParts.join("&") : undefined;
    setReplayLoading(true);
    setReplayError(null);
    setCreatedInvestigation(null);
    setOutcome(null);
    setHistory([]);
    setVerificationHistory([]);
    setInvestigationId(null);
    setVerification(null);
    setEvidenceTimeline([]);
    setHumanReport(null);
    setEvents([]);
    setNotifications([]);
    setCaregiverPermission(null);
    setReplayMetrics(null);
    setRecordedReplay(null);
    setRecordedByAt({});
    setNotificationsError(null);
    setFollowUpTargetTemp(null);
    setReplayAt(null);
    noFollowUpIds.current.clear();
    createInvestigation(scenario, startAt, { signal: controller.signal, queryExtra })
      .then((response) => {
        if (token !== investigationTokenRef.current) return;
        if (response.scenario !== scenario) return;
        setCreatedInvestigation(response);
        setReplayMetrics(response.metrics ?? null);
        setRecordedReplay(response.investigation as unknown as RecordedInvestigation);
        setInvestigationId(response.investigation_id);
        createdAtRef.current = startAt;
        setOutcome(response.outcome);
        setHistory([]);
        if (response.notifications) setNotifications(response.notifications);
        setFollowUpUnit(
          typeof response.follow_up?.target_unit === "string"
            ? response.follow_up.target_unit
            : null,
        );
        setFollowUpTargetTemp(
          typeof response.follow_up?.target_temp === "number"
            ? response.follow_up.target_temp
            : typeof response.follow_up?.target?.target_temp === "number"
              ? response.follow_up.target.target_temp
              : null,
        );
        if (typeof response.follow_up?.target?.target_unit === "string") {
          setFollowUpUnit(response.follow_up.target.target_unit);
        }
        setReplayAt(startAt);
        setReplayLoading(false);
        if (response.follow_up === null) {
          noFollowUpIds.current.add(response.investigation_id);
          return;
        }
        fetchFollowUp(response.investigation_id, startAt)
          .then((followUp) => {
            if (token !== investigationTokenRef.current) return;
            if (followUp.scenario !== scenario) return;
            setOutcome(followUp.outcome);
            setHistory(followUp.history);
            setVerification(followUp.verification ?? null);
            setEvidenceTimeline(followUp.evidence_timeline ?? []);
            setHumanReport(followUp.human_report ?? null);
            setVerificationHistory(followUp.verification_history ?? []);
            setCaregiverPermission(followUp.caregiver_permission ?? null);
            setReplayMetrics(followUp.metrics ?? null);
            setRecordedReplay(followUp.recorded_investigation ?? null);
            if (followUp.notifications) {
              setNotifications(followUp.notifications);
            } else {
              fetchNotifications(response.investigation_id, startAt)
                .then((notifs) => {
                  if (token === investigationTokenRef.current) setNotifications(notifs.notifications);
                })
                .catch(() => undefined);
            }
          })
          .catch(() => undefined);
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        if (token !== investigationTokenRef.current) return;
        setInvestigationId(null);
        if (error instanceof RecoveryRequiredError) {
          setReplayError("Inference recovery required — repeat with retry");
        } else {
          setReplayError("Follow-up not reachable");
        }
        setReplayLoading(false);
      });
    return () => {
      controller.abort();
    };
  }, [scenario, publicMode, storyCheckpoints]);

  useEffect(() => {
    if (!replayAt) return;
    const token = ++eventsTokenRef.current;
    fetchEvents(scenario, replayAt)
      .then((response) => {
        if (token !== eventsTokenRef.current) return;
        if (response.scenario !== scenario) return;
        if (Date.parse(response.at) !== Date.parse(replayAt)) return;
        setEvents(response.events);
      })
      .catch(() => {
        if (token === eventsTokenRef.current) setEvents([]);
      });
  }, [scenario, replayAt]);

  useEffect(() => {
    if (publicMode !== false) return;
    let live = true;
    fetchLivePower().then((response) => {
      if (live) setLivePower(response);
    });
    fetchWhatsappStatus().then((response) => {
      if (live) setWhatsappConfigured(response?.configured ?? false);
    });
    fetchCameraConfigured().then((configured) => {
      if (live) setCameraConfigured(configured);
    });
    return () => {
      live = false;
    };
  }, [publicMode]);

  function handleScenarioChange(nextScenario: string) {
    replayTokenRef.current += 1;
    if (nextScenario !== scenario) {
      investigationTokenRef.current += 1;
    }
    sourcesTokenRef.current += 1;
    contextTokenRef.current += 1;
    setContextData(null);
    setScenario(nextScenario);
    const publicStart =
      publicMode === true && nextScenario === STORY_SCENARIO && storyCheckpoints.length > 0
        ? storyCheckpoints[0]
        : startAtForScenario(nextScenario);
    setSelectedAt(publicStart);
    setSourcesLoading(true);
  }

  function handleReplayTime(at: string) {
    if (!investigationId) return;
    const token = ++replayTokenRef.current;
    setSelectedAt(at);
    setReplayLoading(true);
    setReplayError(null);
    setOutcome(null);
    setHistory([]);
    setVerification(null);
    setEvidenceTimeline([]);
    setHumanReport(null);
    setVerificationHistory([]);
    setEvents([]);
    setNotifications([]);
    setCaregiverPermission(null);
    setReplayMetrics(null);
    setRecordedReplay(null);
    setNotificationsError(null);
    const storyPosition = storyCheckpoints.indexOf(at);
    if (scenario === STORY_SCENARIO && storyPosition >= 0) setStoryIndex(storyPosition);
    const eventsToken = ++eventsTokenRef.current;
    const eventsScenario = scenario;
    fetchEvents(eventsScenario, at)
      .then((response) => {
        if (token !== replayTokenRef.current) return;
        if (eventsToken !== eventsTokenRef.current) return;
        if (response.scenario !== eventsScenario) return;
        if (Date.parse(response.at) !== Date.parse(at)) return;
        setEvents(response.events);
      })
      .catch(() => {
        if (token === replayTokenRef.current && eventsToken === eventsTokenRef.current) setEvents([]);
      });
    const createdWithoutFollowUp =
      noFollowUpIds.current.has(investigationId) ||
      (createdInvestigation !== null &&
        createdInvestigation.investigation_id === investigationId &&
        createdInvestigation.follow_up === null);
    const createdAt = createdAtRef.current;
    const reuseAllowed =
      !createdWithoutFollowUp &&
      (createdAt === null ||
        Number.isNaN(Date.parse(createdAt)) ||
        Number.isNaN(Date.parse(at)) ||
        Date.parse(at) >= Date.parse(createdAt));
    const createFresh = () => createInvestigation(scenario, at).then((created) => {
      if (token !== replayTokenRef.current) return null;
      if (created.follow_up === null) {
        noFollowUpIds.current.add(created.investigation_id);
      } else {
        noFollowUpIds.current.delete(created.investigation_id);
      }
      createdAtRef.current = at;
      setCreatedInvestigation(created);
      setReplayMetrics(created.metrics ?? null);
      setRecordedReplay(created.investigation as unknown as RecordedInvestigation);
      {
        const createdRecorded = created.investigation as unknown as RecordedInvestigation | null;
        if (createdRecorded?.output && typeof createdRecorded.evaluated_at === "string") {
          const key = createdRecorded.evaluated_at;
          setRecordedByAt((prev) => (prev[key] ? prev : { ...prev, [key]: createdRecorded }));
        }
      }
      setInvestigationId(created.investigation_id);
      if (created.notifications) setNotifications(created.notifications);
      if (created.follow_up === null) {
        setOutcome(created.outcome);
        setReplayAt(at);
        setReplayLoading(false);
        return null;
      }
      return fetchFollowUp(created.investigation_id, at);
    });
    const followUpRequest = reuseAllowed
      ? fetchFollowUp(investigationId, at).catch(() => createFresh())
      : createFresh();
    followUpRequest
      .then((response) => {
        if (response === null) return;
        if (token !== replayTokenRef.current) return;
        if (response.scenario !== scenario) return;
        if (response.at && Date.parse(response.at) !== Date.parse(at)) return;
        setOutcome(response.outcome);
        setHistory(response.history);
        setVerification(response.verification ?? null);
        setEvidenceTimeline(response.evidence_timeline ?? []);
        setHumanReport(response.human_report ?? null);
        setVerificationHistory(response.verification_history ?? []);
        setCaregiverPermission(response.caregiver_permission ?? null);
        setReplayMetrics(response.metrics ?? null);
        setRecordedReplay(response.recorded_investigation ?? null);
        {
          const recorded = response.recorded_investigation ?? null;
          if (recorded?.output && typeof recorded.evaluated_at === "string") {
            const key = recorded.evaluated_at;
            setRecordedByAt((prev) => ({ ...prev, [key]: recorded }));
          }
        }
        if (response.follow_up) {
          if (typeof response.follow_up.target_unit === "string") {
            setFollowUpUnit(response.follow_up.target_unit);
          }
          if (typeof response.follow_up.target_temp === "number") {
            setFollowUpTargetTemp(response.follow_up.target_temp);
          } else if (typeof response.follow_up.target?.target_temp === "number") {
            setFollowUpTargetTemp(response.follow_up.target.target_temp);
          }
        }
        if (response.notifications) {
          setNotifications(response.notifications);
          setNotificationsError(null);
        } else {
          fetchNotifications(investigationId, at)
            .then((notifs) => {
              if (token === replayTokenRef.current) setNotifications(notifs.notifications);
            })
            .catch(() => {
              if (token === replayTokenRef.current) setNotificationsError("Notifications not reachable");
            });
        }
        setReplayAt(at);
        setReplayLoading(false);
      })
      .catch(() => {
        if (token !== replayTokenRef.current) return;
        setReplayError("Follow-up not reachable");
        setReplayLoading(false);
      });
  }

  function startStory() {
    if (scenario !== STORY_SCENARIO) {
      handleScenarioChange(STORY_SCENARIO);
    } else if (storyCheckpoints.length > 0 && investigationId) {
      handleReplayTime(storyCheckpoints[0]);
    } else if (storyCheckpoints.length > 0 && selectedAt !== storyCheckpoints[0]) {
      setSelectedAt(storyCheckpoints[0]);
    } else if (storyCheckpoints.length === 0 && selectedAt !== CARE_START_AT) {
      setSelectedAt(CARE_START_AT);
    }
    setStoryIndex(0);
    setEvidenceOpen(false);
    setPage("house");
    setView("story");
  }

  function stepTo(index: number) {
    if (storyCheckpoints.length === 0) return;
    const next = Math.min(Math.max(index, 0), storyCheckpoints.length - 1);
    setStoryIndex(next);
    handleReplayTime(storyCheckpoints[next]);
  }

  function exploreFreely() {
    setEvidenceOpen(false);
    setPage("house");
    setView("free");
  }

  function openLaws() {
    setEvidenceOpen(false);
    setLawsOpen(true);
    setPage("reasoning");
    if (view === "landing") setView("free");
  }

  function openTrace() {
    setEvidenceOpen(false);
    setPage("reasoning");
    if (view === "landing") setView("free");
  }

  function backToLanding() {
    setEvidenceOpen(false);
    setView("landing");
  }

  function handleResetSession() {
    setResetting(true);
    setResetError(null);
    resetPublicSession()
      .then(() => {
        window.location.reload();
      })
      .catch(() => {
        setResetting(false);
        setResetError("Reset not reachable — please reload the page");
      });
  }

  function handleAck(notification: Notification) {
    setAckingId(notification.id);
    ackNotification(notification.id, notification.audience, replayAt ?? undefined)
      .then((response) => {
        const updated = response.notification;
        const withAcks = updated.acks?.length ? updated : { ...updated, acks: response.acks };
        setNotifications((current) =>
          current.map((item) => (item.id === withAcks.id ? withAcks : item)),
        );
        setAckingId(null);
      })
      .catch(() => {
        setNotificationsError("Notifications not reachable");
        setAckingId(null);
      });
  }

  function handleCaregiverDecision(decision: "approve" | "decline") {
    if (!caregiverPermission || !investigationId || !replayAt) return;
    const at = replayAt;
    const id = investigationId;
    setDecidingPermission(true);
    decideCaregiverPermission(caregiverPermission.notification_id, decision, at)
      .then(() => fetchFollowUp(id, at))
      .then((response) => {
        setCaregiverPermission(response.caregiver_permission ?? null);
        setReplayMetrics(response.metrics ?? null);
        setRecordedReplay(response.recorded_investigation ?? null);
        {
          const recorded = response.recorded_investigation ?? null;
          if (recorded?.output && typeof recorded.evaluated_at === "string") {
            const key = recorded.evaluated_at;
            setRecordedByAt((prev) => ({ ...prev, [key]: recorded }));
          }
        }
        if (response.notifications) setNotifications(response.notifications);
        setDecidingPermission(false);
      })
      .catch(() => {
        setNotificationsError("Notifications not reachable");
        setDecidingPermission(false);
      });
  }

  function handleSendWhatsapp(notification: Notification) {
    setSendingWhatsappId(notification.id);
    sendHvacWhatsapp(notification.id, replayAt ?? undefined)
      .then((response) => {
        const updated = response.notification;
        setNotifications((current) =>
          current.map((item) => (item.id === updated.id ? { ...item, ...updated } : item)),
        );
        setSendingWhatsappId(null);
      })
      .catch(() => {
        setNotificationsError("Notifications not reachable");
        setSendingWhatsappId(null);
      });
  }

  const verifiedFacts = createdInvestigation?.investigation?.output?.verified_facts ?? [];

  const displayInvestigation = createdInvestigation
    ? ({
        ...createdInvestigation.investigation,
        data_mode: "synthetic",
        evaluated_at: createdInvestigation.investigation.evaluated_at,
      } as unknown as InvestigationResponse)
    : null;
  const reasoningInvestigation =
    publicMode === true ? (recordedReplay ?? displayInvestigation) : displayInvestigation;

  const visibleNotifications = notifications.filter((notification) => {
    if (!replayAt) return true;
    const createdMs = Date.parse(notification.created_at);
    const replayMs = Date.parse(replayAt);
    if (Number.isNaN(createdMs) || Number.isNaN(replayMs) || createdMs <= replayMs) return true;
    return (
      notification.audience === "hvac_company" &&
      notification.state === "simulated_delivered" &&
      events.some((event) => event.kind === "hvac_request")
    );
  });

  const inStory = publicMode === true && view === "story" && storyCheckpoints.length > 0;
  const storyAt = inStory ? storyCheckpoints[Math.min(storyIndex, storyCheckpoints.length - 1)] : null;
  const storyTitle = STORY_STEP_TITLES[Math.min(storyIndex, STORY_STEP_TITLES.length - 1)] ?? "";
  const storyGuidance = STORY_STEP_GUIDANCE[Math.min(storyIndex, STORY_STEP_GUIDANCE.length - 1)] ?? "";
  const earlierInvestigations = inStory
    ? storyCheckpoints
      .slice(0, Math.min(storyIndex, storyCheckpoints.length))
      .map((checkpoint) => recordedByAt[checkpoint])
      .filter((item): item is RecordedInvestigation =>
        !!item?.output && typeof item.evaluated_at === "string" &&
        !Number.isNaN(Date.parse(item.evaluated_at)) && !Number.isNaN(Date.parse(selectedAt)) &&
        Date.parse(item.evaluated_at) < Date.parse(selectedAt),
      )
    : [];
  const deterministicReadiness =
    createdInvestigation?.readiness ?? displayInvestigation?.summary?.readiness ?? null;
  const recordedProvenance =
    (createdInvestigation?.investigation as unknown as
      | { recorded_provenance?: Record<string, unknown> }
      | null
      | undefined)?.recorded_provenance ?? null;
  const replayTimes =
    scenario === VIDEO_SCENARIO
      ? VIDEO_REPLAY_TIMES
      : scenario === CARE_SCENARIO
        ? CARE_REPLAY_TIMES
        : REPLAY_TIMES;
  const stepperTimes =
    inStory && storyCheckpoints.length > 0
      ? storyCheckpoints.map((at) => ({ label: at.slice(11, 16), at }))
      : replayTimes;
  const verdict = !replayLoading || deterministicReadiness || verification
    ? buildVerdict(deterministicReadiness, verification, followUpTargetTemp, followUpUnit)
    : null;
  const trend = replayMetrics?.indoor_trend ?? null;
  const gapTarget = replayMetrics?.target_gap ?? null;
  const warmByTargetTemp = followUpTargetTemp ?? gapTarget?.target_temp ?? null;
  const warmByTargetUnit = followUpUnit ?? gapTarget?.target_unit ?? null;
  const plannedArrival = contextData?.planned_arrival ?? null;
  const lead = buildLead(data?.sources, trend);
  const gapCallout = gapCalloutFor(data?.sources);
  const visualEnabled =
    publicMode === false || scenario !== STORY_SCENARIO || storyCheckpoints.includes(selectedAt);
  const reasoningReady = visualEnabled;
  const traceInvestigationId = (() => {
    if (investigationId === null || replayAt === null) return null;
    if (Number.isNaN(Date.parse(selectedAt)) || Number.isNaN(Date.parse(replayAt))) return null;
    if (Date.parse(selectedAt) !== Date.parse(replayAt)) return null;
    if (noFollowUpIds.current.has(investigationId)) return null;
    if (
      createdInvestigation !== null &&
      createdInvestigation.investigation_id === investigationId &&
      createdInvestigation.follow_up === null
    )
      return null;
    const createdAt = createdAtRef.current;
    if (
      createdAt !== null &&
      !Number.isNaN(Date.parse(createdAt)) &&
      Date.parse(selectedAt) < Date.parse(createdAt)
    )
      return null;
    return investigationId;
  })();
  const pillText =
    scenario === STORY_SCENARIO
      ? "Synthetic demo · demo-house, Petoskey"
      : `Synthetic demo · ${scenario}`;
  const homeownerReady = verification?.stage === "arrival_met" && followUpTargetTemp !== null;

  const integrationRows: Array<{ name: string; status: string; tone: StatusTone; note: string }> = [
    whatsappConfigured || publicMode !== true
      ? {
          name: "WhatsApp",
          status: publicMode === true ? "Simulated" : whatsappConfigured ? "Configured" : "Off",
          tone: publicMode === true || !whatsappConfigured ? "unknown" : "ok",
          note: publicMode === true
            ? "Caregiver permission and HVAC notice; simulated in this demo; real only on the owner's test number when opted in"
            : "Caregiver permission and HVAC notice",
        }
      : {
          name: "WhatsApp",
          status: "Off",
          tone: "unknown",
          note: "Caregiver permission and HVAC notice",
        },
    {
      name: "Emporia energy",
      status: publicMode === true ? "Off" : livePower?.status === "ok" ? "Live" : "Off",
      tone: publicMode === true || livePower?.status !== "ok" ? "unknown" : "ok",
      note:
        publicMode === true
          ? "Off in this demo"
          : livePower?.status === "ok"
            ? `${livePower.source} — read-only, display only`
            : "Not connected",
    },
    {
      name: "Nest camera",
      status: publicMode === true ? "Off" : cameraConfigured ? "On" : "Off",
      tone: publicMode === true || !cameraConfigured ? "unknown" : "ok",
      note:
        publicMode === true
          ? "Owner's mechanical room; off in this demo"
          : "Owner's mechanical room",
    },
    {
      name: "Synthetic camera frames",
      status: "Recorded",
      tone: "unknown",
      note: "Recorded sam-3.1 segmentation of the synthetic frames",
    },
    ...(["room_sensor", "thermostat", "weather", "calendar"] as SourceKind[]).map((kind) => {
      const status = sourceByKind(data?.sources, kind);
      return {
        name: kind === "room_sensor" ? "Room sensor" : kind === "thermostat" ? "Thermostat" : kind === "weather" ? "Weather" : "Calendar",
        status: status ? AVAILABILITY_LABEL[status.availability] : "Unknown",
        tone: status ? availabilityTone(status.availability) : ("unknown" as StatusTone),
        note:
          kind === "weather"
            ? "Forecast, not an on-property measurement."
            : status?.notes[0] ?? (status ? `newest observed ${formatTimestamp(status.newest_observed_at)}` : "no readings"),
      };
    }),
  ];

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      window.localStorage.setItem("aria-home-theme", theme);
    } catch {
      // storage unavailable; the choice still applies for this session
    }
  }, [theme]);

  useEffect(() => {
    if (!inset || insetPanels.length === 0) return;
    if (INSET_TARGETS[inset]?.includes("investigation") || inset === "evidence-timeline") {
      setPage("reasoning");
    } else {
      setPage("house");
    }
  }, []);

  if (publicMode === true && (view === "landing" || view === null)) {
    return (
      <div className="page public-landing">
        <AppHeader
          page="house"
          onPage={() => undefined}
          showNav={false}
          pillText="Synthetic demo · demo-house, Petoskey"
          pillTone="unknown"
          times={[]}
          selectedAt={storyCheckpoints[0] ?? CARE_START_AT}
          onStep={() => undefined}
          canStep={false}
          theme={theme}
          onToggleTheme={() => setTheme(theme === "dark" ? "light" : "dark")}
        />
        <main>
          <div className="landing-letter">
            <p className="landing-eyebrow">A demo for the Meta AI hackathon</p>
            <h1>Will an older adult's home be warm by morning, and if something looks wrong overnight, who should respond?</h1>
            <p>ARIA Home watches a synthetic winter night and gets the right person moving when something looks wrong.</p>
            <blockquote className="brad-hook">{BRAD_HOOK}</blockquote>
            <div className="household-card">
              <p>demo-house · Petoskey, Michigan · synthetic · warm-by 68 F at 7:00 · caregiver: her daughter</p>
            </div>
            <div className="landing-actions">
              <button type="button" className="btn-primary" onClick={startStory} autoFocus>
                Start the warm-by story
              </button>
              <button type="button" className="link-button" onClick={exploreFreely}>
                Explore the app freely
              </button>
            </div>
            <div className="session-controls">
              <button type="button" className="link-button" onClick={handleResetSession} disabled={resetting}>
                {resetting ? "Resetting…" : "Reset my session"}
              </button>
              {resetError && (
                <p role="alert" className="error">
                  {resetError}
                </p>
              )}
            </div>
          </div>
        </main>
        <VersionLine commit={version} />
      </div>
    );
  }

  return (
    <div className={`page${inset && insetPanels.length ? ` inset-active inset-${inset}` : ""}${keyCaption ? ` key-active key-${keyName}` : ""}`}>
      <AppHeader
        page={page}
        onPage={setPage}
        showNav={view !== "landing"}
        pillText={pillText}
        pillTone={verdict?.tone ?? "unknown"}
        times={stepperTimes}
        selectedAt={selectedAt}
        onStep={handleReplayTime}
        canStep={investigationId !== null}
        theme={theme}
        onToggleTheme={() => setTheme(theme === "dark" ? "light" : "dark")}
      />
      <main>
      {data && publicMode !== true && (
        <p className="banner" role="status" hidden={page !== "house"}>
          {data.data_mode.toUpperCase()} DATA - demo scenario, not a real home{" "}
          <span className="banner-mode">(data mode: {data.data_mode})</span>
        </p>
      )}

      {publicMode !== true && (
        <header hidden={page !== "house"}>
          <h1>Will an older adult's home be warm by morning, and if something looks wrong overnight, who should respond?</h1>
        </header>
      )}
      <div className="letter-block" hidden={page !== "house"}>
        <p className="verdict-eyebrow">{formatLongTime(selectedAt)}</p>
        {verdict ? (
          <>
            <h1 className="verdict-headline">{verdict.headline}</h1>
            {lead && <p className="verdict-lead">{lead}</p>}
            {gapCallout && (
              <div className="gap-callout" role="note">
                <span className="status-dot status-dot-watch" aria-hidden="true" />
                <p>{gapCallout}</p>
              </div>
            )}
          </>
        ) : (
          <p role="status">Checking the house…</p>
        )}
      </div>
      {inStory && (
        <section aria-labelledby="story-heading" className="story-panel" hidden={page !== "house"}>
          <p className="story-eyebrow story-progress" role="status">
            Step {Math.min(storyIndex + 1, storyCheckpoints.length)} of {storyCheckpoints.length} ·{" "}
            {storyAt ? shortTimeLabel(storyAt) : "…"}
          </p>
          <h2 id="story-heading" aria-label={`Step ${Math.min(storyIndex + 1, storyCheckpoints.length)} of ${storyCheckpoints.length} — ${storyTitle} (The warm-by story)`}>{storyTitle}</h2>
          <p>{storyGuidance}</p>
          {evidenceTimeline.length > 0 && (
            <p className="story-known-line">
              Known at this step:{" "}
              {evidenceTimeline
                .map(
                  (entry) =>
                    `${entry.label} — observed ${formatTimestamp(entry.observed_at)}, first known ${formatTimestamp(entry.first_known_at)}${entry.corroboration_only ? " (corroboration only)" : ""}`,
                )
                .join("; ")}
            </p>
          )}
          <p className="story-caregiver-caption" data-testid="story-caregiver-caption" role="status">
            {caregiverPermission
              ? `${caregiverStatusCopy(caregiverPermission).headline} ${caregiverStatusCopy(caregiverPermission).effect} Asked at ${formatTimestamp(caregiverPermission.requested_at)}.`
              : "No caregiver request at this step."}
          </p>
          <div className="story-nav">
            <button type="button" className="ghost-button" onClick={() => stepTo(0)} disabled={storyIndex === 0 || !investigationId}>
              Rewind to start
            </button>
            <button
              type="button"
              className="ghost-button"
              onClick={() => stepTo(storyIndex - 1)}
              disabled={storyIndex === 0 || !investigationId}
            >
              Back
            </button>
            <button
              type="button"
              className="btn-primary"
              onClick={() => stepTo(storyIndex + 1)}
              disabled={storyIndex >= storyCheckpoints.length - 1 || !investigationId}
            >
              {storyIndex >= storyCheckpoints.length - 1 ? "Story complete" : "Next"}
            </button>
            <button type="button" className="ghost-button" onClick={openTrace} disabled={!investigationId}>
              See ARIA&rsquo;s view of this step
            </button>
          </div>
          {storyIndex >= storyCheckpoints.length - 1 && (
            <p className="story-complete" role="status">
              Story complete — the home reached and held 68 F before the 07:00 warm-by time. Explore the evidence or
              reset your session to run it again.
            </p>
          )}
        </section>
      )}
      {evidenceOpen && publicMode === true && (
        <aside
          aria-label="Explore evidence"
          className="evidence-drawer"
          hidden={page !== "house"}
          onKeyDown={(event) => {
            if (event.key === "Escape") setEvidenceOpen(false);
          }}
        >
          <div className="drawer-head">
            <h2>Explore evidence</h2>
            <button type="button" className="ghost-button" onClick={() => setEvidenceOpen(false)} autoFocus>
              Close evidence
            </button>
          </div>
          <p>Synthetic, reviewed fields only. No raw audit data.</p>
          <section aria-labelledby="drawer-sources-heading">
            <h3 id="drawer-sources-heading">Sources</h3>
            {!data ? (
              <p role="status">Loading sources…</p>
            ) : (
              <ul>
                {data.sources.map((status) => (
                  <li key={status.source}>
                    {status.source}: {AVAILABILITY_LABEL[status.availability]} — newest observed{" "}
                    {formatTimestamp(status.newest_observed_at)}, age {formatAge(status.age_s)}
                    {status.notes.length > 0 ? ` (${status.notes.join("; ")})` : ""} (synthetic,
                    received by {formatTimestamp(data.at)})
                  </li>
                ))}
              </ul>
            )}
          </section>
          <section aria-labelledby="drawer-readiness-heading">
            <h3 id="drawer-readiness-heading">Readiness (computed by code)</h3>
            {!deterministicReadiness ? (
              <p role="status">Loading readiness…</p>
            ) : (
              <>
                <p>Status: {READINESS_LABEL[deterministicReadiness.status]}</p>
                <ul>
                  {deterministicReadiness.reasons.map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
              </>
            )}
          </section>
          <section aria-labelledby="drawer-verification-heading">
            <h3 id="drawer-verification-heading">Verification (computed by code)</h3>
            {!verification ? (
              <p role="status">{replayLoading ? "Loading verification…" : "No verification yet."}</p>
            ) : (
              <>
                <p>Stage: {VERIFICATION_LABEL[verification.stage]}</p>
                <ul>
                  {verification.reasons.map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
                <p>Only later measurements advance a stage; acknowledgements, visits and the HVAC report do not.</p>
              </>
            )}
          </section>
          <section aria-labelledby="drawer-model-heading">
            <h3 id="drawer-model-heading">Model interpretation and limits</h3>
            {reasoningInvestigation?.output ? (
              <>
                <p>
                  {reasoningInvestigation.provider_mode === "recorded"
                    ? "Recorded model response (not live inference)."
                    : "MOCK - example answer, not live inference."}
                </p>
                <p>{reasoningInvestigation.output.interpretation}</p>
                {reasoningInvestigation.output.limitations.length > 0 && (
                  <ul>
                    {reasoningInvestigation.output.limitations.map((limitation) => (
                      <li key={limitation}>{limitation}</li>
                    ))}
                  </ul>
                )}
                {recordedProvenance ? (
                  <p>
                    Model: {String(recordedProvenance["model_id"] ?? "unknown")} — route{" "}
                    {String(recordedProvenance["provider_route"] ?? "unknown")}, recorded{" "}
                    {String(recordedProvenance["recorded_at"] ?? "unknown")}, input revision{" "}
                    {String(recordedProvenance["input_revision"] ?? "unknown")}, code snapshot{" "}
                    {String(recordedProvenance["code_snapshot"] ?? "unknown")}.
                  </p>
                ) : (
                  <p>Provenance: provider mode {reasoningInvestigation.provider_mode ?? "unknown"}.</p>
                )}
              </>
            ) : (
              <>
                <p>{NO_RECORDED_LABEL} — showing the deterministic summary instead.</p>
                {deterministicReadiness && (
                  <ul>
                    {deterministicReadiness.reasons.map((reason) => (
                      <li key={reason}>{reason}</li>
                    ))}
                  </ul>
                )}
              </>
            )}
          </section>
          <section aria-labelledby="drawer-notices-heading">
            <h3 id="drawer-notices-heading">Notices: fields sent and refused</h3>
            {visibleNotifications.length === 0 ? (
              <p>No notices visible at this step.</p>
            ) : (
              <ul>
                {visibleNotifications.map((notification) => (
                  <li key={notification.id}>
                    {NOTIFICATION_AUDIENCE_LABEL[notification.audience] ?? notification.audience}:{" "}
                    {notificationStateInWords(notification)} — fields sent:{" "}
                    {Object.keys(notification.payload).join(", ")}
                  </li>
                ))}
              </ul>
            )}
          </section>
          <section aria-labelledby="drawer-models-heading">
            <h3 id="drawer-models-heading">Model contributions</h3>
            <ul>
              {MODEL_CONTRIBUTIONS.map((item) => (
                <li key={item.model}>
                  {item.model} — {item.role}. {item.status}.
                </li>
              ))}
            </ul>
          </section>
        </aside>
      )}
      {publicMode !== true && (
      <section className="demo-controls" aria-label="Demo controls" hidden={page !== "house"}>
        <p className="demo-controls-title">Demo controls (synthetic replay)</p>
        <label className="demo-scenario">
          Scenario{" "}
          <select
            aria-label="Scenario"
            value={scenario}
            onChange={(event) => handleScenarioChange(event.target.value)}
          >
            {SCENARIOS.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <div className="demo-times" role="group" aria-label="Replay time">
          {(scenario === VIDEO_SCENARIO ? VIDEO_REPLAY_TIMES : scenario === CARE_SCENARIO ? CARE_REPLAY_TIMES : REPLAY_TIMES).map((time) => (
            <button
              key={time.at}
              type="button"
              className="ghost-button"
              onClick={() => handleReplayTime(time.at)}
              disabled={!investigationId}
              aria-pressed={selectedAt === time.at}
              aria-label={`Replay to ${time.label}`}
            >
              {time.label}
            </button>
          ))}
        </div>
        <button type="button" className="ghost-button" onClick={openLaws}>
          ARIA&rsquo;s Laws
        </button>
        <button type="button" className="ghost-button" onClick={openTrace}>
          ARIA&rsquo;s view
        </button>
      </section>
      )}
      <div hidden={page !== "house"}>
        <GlanceTiles
          sources={data?.sources}
          trend={trend}
          targetTemp={warmByTargetTemp}
          targetUnit={warmByTargetUnit}
          plannedArrival={plannedArrival}
          verdictTone={verdict?.tone ?? "unknown"}
          scenario={scenario}
          at={selectedAt}
          visualEnabled={visualEnabled}
        />
      </div>
      <div hidden={page !== "house"}>
        <WhoKnows
          permission={caregiverPermission}
          onDecide={handleCaregiverDecision}
          deciding={decidingPermission}
          whatsappConfigured={whatsappConfigured}
          onSendWhatsapp={() => {
            const alert = notifications.find((item) => item.id === caregiverPermission?.notification_id);
            if (alert) handleSendWhatsapp(alert);
          }}
          sending={sendingWhatsappId === caregiverPermission?.notification_id}
          notifications={visibleNotifications}
          notificationsError={notificationsError}
          onAck={handleAck}
          ackingId={ackingId}
          onSendWhatsappFor={handleSendWhatsapp}
          sendingWhatsappId={sendingWhatsappId}
          homeownerReady={homeownerReady}
          sectionClassName={insetClass("notifications")}
        />
      </div>

      {reasoningReady && (
      <div hidden={page !== "reasoning"}>
        <SectionBoundary name="ARIA's view" key={`trace-${selectedAt}`}>
        <TraceView
          scenario={scenario}
          at={selectedAt}
          times={replayTimes}
          onSelectAt={handleReplayTime}
          onBack={() => setPage("house")}
          active={page === "reasoning"}
          investigationId={traceInvestigationId}
        />
        </SectionBoundary>
      </div>
      )}
      {reasoningReady && (
      <div hidden={page !== "reasoning"}>
        <SectionBoundary name="Code checks" key={`checks-${selectedAt}`}>
        <CodeChecks scenario={scenario} at={selectedAt} active={page === "reasoning"} />
        </SectionBoundary>
      </div>
      )}

      <section aria-labelledby="investigation-heading" className={insetClass("investigation")} hidden={page !== "reasoning"}>
        <SectionBoundary name="Investigation" key={`investigation-${selectedAt}`}>
        <p className="section-label">What the model said</p>
        <h2 id="investigation-heading">Investigation</h2>
        {publicMode === true && reasoningInvestigation?.provider_mode === "recorded" && (
          <p>Recorded model response — recorded, not live.</p>
        )}
        <InvestigationSection data={reasoningInvestigation} error={investigationError} created={createdInvestigation} replayAt={selectedAt} earlier={earlierInvestigations} />
        </SectionBoundary>
      </section>

      <section aria-labelledby="outcome-heading" className={insetClass("outcome")} hidden={page !== "house"}>
        <p className="section-label">Recovery</p>
        <h2 id="outcome-heading">Recovery so far</h2>
        <OutcomeSection
          outcome={outcome}
          history={history}
          verificationHistory={verificationHistory}
          replayAt={replayAt}
          unit={followUpUnit}
          error={replayError}
          loading={replayLoading}
          verification={verification}
          notScheduled={
            outcome === null &&
            !replayLoading &&
            createdInvestigation !== null &&
            createdInvestigation.follow_up === null &&
            createdInvestigation.schedule_status === "not_scheduled"
          }
        />
      </section>

      <section aria-labelledby="evidence-timeline-heading" className={insetClass("evidence-timeline")} hidden={page !== "reasoning"}>
        <SectionBoundary name="Evidence timeline" key={`evidence-timeline-${selectedAt}`}>
        <p className="section-label">Evidence timeline</p>
        <h2 id="evidence-timeline-heading">Evidence timeline</h2>
        <EvidenceTimelineSection entries={evidenceTimeline} />
        <p className="section-label">Human reports</p>
        <HumanReportSection report={humanReport} />
        </SectionBoundary>
      </section>

      <div hidden={page !== "house"}>
        <HomeownerUpdateCard
          verification={verification}
          targetTemp={followUpTargetTemp}
          targetUnit={followUpUnit}
          verifiedFacts={verifiedFacts}
          sectionClassName={insetClass("homeowner")}
        />
      </div>

      <section aria-labelledby="timeline-heading" className={insetClass("timeline")} hidden={page !== "reasoning"}>
        <SectionBoundary name="Simulated timeline" key={`timeline-${selectedAt}`}>
        <p className="section-label">Simulated events</p>
        <h2 id="timeline-heading">Simulated timeline</h2>
        <SimulatedTimeline events={events} replayAt={replayAt} />
        </SectionBoundary>
      </section>

      <section aria-labelledby="confirmed-plan-heading" className={insetClass("plan")} hidden={page !== "house"}>
        <details className="plan-row">
          <summary id="confirmed-plan-heading">The plan</summary>
          <ConfirmedPlanSection data={contextData} error={contextError} />
        </details>
      </section>

      {inStory && storyIndex < storyCheckpoints.length - 1 && (
        <div className="bottom-nav" hidden={page !== "house"}>
          <button
            type="button"
            className="btn-primary"
            onClick={() => stepTo(storyIndex + 1)}
            disabled={!investigationId}
            aria-label="Next step"
          >
            Next
          </button>
        </div>
      )}
      <div className="house-footer-controls" hidden={page !== "house"}>
        {publicMode === true && view !== "landing" && (
          <button type="button" className="ghost-button" onClick={backToLanding}>
            Back to start
          </button>
        )}
        {publicMode === true && (
          <button type="button" className="ghost-button" onClick={() => setEvidenceOpen((open) => !open)} aria-expanded={evidenceOpen}>
            {evidenceOpen ? "Close evidence" : "Explore evidence"}
          </button>
        )}
        {publicMode === true && (
          <button type="button" className="ghost-button" onClick={handleResetSession} disabled={resetting}>
            {resetting ? "Resetting…" : "Reset my session"}
          </button>
        )}
        {resetError && (
          <p role="alert" className="error">
            {resetError}
          </p>
        )}
      </div>

      <section aria-labelledby="evidence-heading" className={insetClass("evidence")} hidden={page !== "reasoning"}>
        <SectionBoundary name="Evidence sources" key={`evidence-${selectedAt}`}>
        <p className="section-label">Sources</p>
        <h2 id="evidence-heading">Evidence sources</h2>
        {sourcesLoading && data && (
          <p role="status" className="stale-evidence">
            Stale evidence — loading the selected scenario and replay time…
          </p>
        )}
        {sourcesLoading && <p role="status">Loading evidence…</p>}
        {!data && !error && !sourcesLoading && <p role="status">Loading evidence…</p>}
        {error && (
          <p role="alert" className="error">
            Backend not reachable
          </p>
        )}
        {data && data.sources.length === 0 && <p role="status">No evidence sources reported.</p>}
        {data && data.sources.length > 0 && (
          <EvidenceSourcesTable sources={data.sources} />
        )}
        </SectionBoundary>
      </section>
      {(scenario.startsWith("visual_") || scenario === CARE_SCENARIO) && (
        <section aria-labelledby="visual-heading" className={insetClass("visual")} hidden={page !== "reasoning"}>
          <SectionBoundary name="Visual evidence" key={`visual-${selectedAt}`}>
          <h2 id="visual-heading">Visual evidence (synthetic image)</h2>
          <VisualEvidencePanel
            scenario={scenario}
            at={selectedAt}
            enabled={visualEnabled}
          />
          </SectionBoundary>
        </section>
      )}
      {reasoningReady && (
      <div hidden={page !== "reasoning"}>
        <SectionBoundary name="ARIA's Laws" key={`laws-${selectedAt}`}>
        <details
          className="laws-details"
          open={lawsOpen}
          onToggle={(event) => setLawsOpen(event.currentTarget.open)}
        >
          <summary>ARIA&rsquo;s Laws</summary>
          <LawsView
            scenario={scenario}
            at={selectedAt}
            onBack={() => setPage("house")}
            active={page === "reasoning"}
          />
        </details>
        </SectionBoundary>
      </div>
      )}
      <section aria-labelledby="integrations-heading" hidden={page !== "integrations"}>
        <p className="section-label">What ARIA is connected to</p>
        <h2 id="integrations-heading">Integrations</h2>
        <ul className="int-rows">
          {integrationRows.map((row) => (
            <li key={row.name} className="int-row">
              <span className={`status-dot status-dot-${row.tone}`} aria-hidden="true" />
              <div className="int-row-body">
                <p className="int-row-title">{row.name}</p>
                <p className="int-row-meta">{row.note}</p>
              </div>
              <span className="int-row-status">{row.status}</span>
            </li>
          ))}
        </ul>
        <h3>Meta models</h3>
        <p>Model answers decide nothing — readiness, verification and notices are computed by code.</p>
        <ul className="models-list">
          {MODEL_CONTRIBUTIONS.map((item) => (
            <li key={item.model}>
              <span className="model-name">{item.model}</span>
              <p>
                {item.role}. {item.status}.
              </p>
            </li>
          ))}
        </ul>
      </section>
      {livePower && livePower.status === "ok" && (
        <section aria-labelledby="live-power-heading" hidden={page !== "integrations" || publicMode !== false}>
          <h2 id="live-power-heading">Your real home, right now (live, read-only, Emporia Vue)</h2>
          <LivePowerPanel data={livePower} />
        </section>
      )}
      {cameraConfigured && (
        <section aria-labelledby="live-camera-heading" hidden={page !== "integrations" || publicMode !== false}>
          <h2 id="live-camera-heading">Live camera (owner&rsquo;s mechanical room)</h2>
          <LiveCameraPanel />
        </section>
      )}
      </main>
      <VersionLine commit={version} />
      {keyCaption && <p className="key-caption">{keyCaption}</p>}
    </div>
  );
}
