import { useEffect, useRef, useState } from "react";
import {
  ackNotification,
  createInvestigation,
  fetchContext,
  fetchEvents,
  fetchFollowUp,
  fetchLivePower,
  fetchNotifications,
  fetchSources,
  RecoveryRequiredError,
  type Availability,
  type ContextFlags,
  type ContextResponse,
  type CreateInvestigationResponse,
  type EvidenceTimelineEntry,
  type InvestigationResponse,
  type InvestigationSummary,
  type LivePowerResponse,
  type Notification,
  type NotificationAudience,
  type OutcomeHistoryEntry,
  type OutcomeResult,
  type OutcomeStatus,
  type Readiness,
  type ReadinessResult,
  type ScenarioEvent,
  type SourceKind,
  type SourceStatus,
  type SourcesResponse,
  type VerificationHistoryEntry,
  type VerificationResult,
  type VerificationStage,
} from "./api";
import "./index.css";

const SCENARIOS = [
  { id: "demo_v1", label: "No recovery" },
  { id: "demo_recovery_v1", label: "Manager report, late warming" },
  { id: "demo_no_followup_v1", label: "No follow-up readings" },
  { id: "demo_video_v1", label: "Trip home, thermostat offline (video)" },
];

const VIDEO_SCENARIO = "demo_video_v1";
const VIDEO_START_AT = "2026-01-16T16:31:00-05:00";

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

const VERIFICATION_LABEL: Record<VerificationStage, string> = {
  telemetry_missing: "Thermostat telemetry missing",
  reporting_restored: "Thermostat reporting restored",
  warming_observed: "Warming observed",
  goal_verified: "Temperature goal verified",
  goal_not_maintained: "Temperature goal no longer maintained",
  arrival_met: "Arrival expectation met",
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

const SOURCE_ORDER: SourceKind[] = ["calendar", "thermostat", "electrical", "weather"];

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
  arrival_passed: "Arrival passed",
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
  return scenarioId === VIDEO_SCENARIO ? VIDEO_START_AT : REPLAY_START_AT;
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
  planned_arrival: "Planned arrival",
  property_label: "Property",
  property: "Property",
  requested_action: "Requested action",
  access_note: "Access note",
  manager_contact_label: "Manager contact",
  manager_contact: "Manager contact",
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
  hvac_request: "HVAC request",
  service_visit: "Service visit",
  hvac_completion_report: "HVAC completion report",
};

const VALUE_LABELS: Record<string, string> = {
  homeowner: "Homeowner",
  property_manager: "Property manager",
  hvac_company: "HVAC company",
  investigation_update: "Investigation update",
  manager_alert: "Manager alert",
  hvac_request: "HVAC request",
  on_track: "On track",
  at_risk: "At risk",
  cannot_tell: "Cannot tell",
  arrival_passed: "Arrival passed",
  telemetry_missing: "Thermostat telemetry missing",
  reporting_restored: "Thermostat reporting restored",
  warming_observed: "Warming observed",
  goal_verified: "Temperature goal verified",
  goal_not_maintained: "Temperature goal no longer maintained",
  arrival_met: "Arrival expectation met",
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
  if (flags?.trip_cancelled) notes.push("Context note: Trip cancelled.");
  if (flags?.trip_unconfirmed) notes.push("Context note: Trip or confirmation unconfirmed.");
  if (flags?.confirmation_outdated)
    notes.push("Context note: Outdated confirmation — confirmation is outdated for the current trip.");
  if (flags?.trip_mismatched)
    notes.push("Context note: Trip and confirmation mismatch — they do not match.");
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
        <ul>
          {readiness.reasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function PowerContextBlock({ summary }: { summary: InvestigationSummary }) {
  const statement = summary.power_context_statement ?? summary.power_context?.statement;
  const limitations = summary.power_context?.limitations ?? [];
  if (!statement && limitations.length === 0) return null;
  return (
    <div className="power-context">
      <h3>Power context</h3>
      {statement && <p>{statement}</p>}
      {limitations.length > 0 && (
        <>
          <p className="power-context-label">Limitations:</p>
          <ul>
            {limitations.map((limitation) => (
              <li key={limitation}>{limitation}</li>
            ))}
          </ul>
        </>
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
          {flags?.confirmation_outdated ? "Confirmation outdated" : flags?.trip_cancelled ? "Trip cancelled" : flags?.trip_mismatched ? "Trip and confirmation do not match" : "Not yet confirmed"}
        </p>
        {data.reason_in_words && data.reason_in_words !== "Not yet confirmed" && <p>{data.reason_in_words}</p>}
        {flags?.confirmation_outdated && <p>Confirmation outdated for the current trip — the confirmed plan no longer matches the current trip revision.</p>}
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
            <dt>Planned arrival</dt>
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
          <dt>Manager coordination</dt>
          <dd>{data.manager_authorized ? "Manager coordination allowed" : "Manager coordination not allowed"}</dd>
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
      {allowances.length > 0 && <p>Arrival times and allowances are scenario estimates, not live travel claims.</p>}
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
}: {
  data: InvestigationResponse | null;
  error: string | null;
  created: CreateInvestigationResponse | null;
  replayAt: string | null;
}) {
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
          <ul>
            {output.verified_facts.map((fact) => (
              <li key={fact}>{fact}</li>
            ))}
          </ul>
        )}
      </div>

      <ReadinessBlock readiness={computedReadiness} gapLine={gapLine} />

      <div className="investigation-block interpretation">
        <h3>Interpretation (model-written, not verified)</h3>
        <p>{output.interpretation}</p>
        {output.limitations.length > 0 && (
          <>
            <p className="power-context-label">Limitations:</p>
            <ul>
              {output.limitations.map((limitation) => (
                <li key={limitation}>{limitation}</li>
              ))}
            </ul>
          </>
        )}
      </div>

      <div className="investigation-block possible-explanations">
        <h3>Possible explanations (not confirmed)</h3>
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

      <ContextNotes flags={flags} deadlinePassed={deadlinePassed} scheduleStatus={scheduleStatus} />

      <h3>What we don&apos;t know</h3>
      {output.unknowns.length === 0 ? (
        <p>Nothing listed.</p>
      ) : (
        <ul>
          {output.unknowns.map((unknown) => (
            <li key={unknown}>{unknown}</li>
          ))}
        </ul>
      )}

      <h3>One question for you</h3>
      <p>{output.clarification}</p>

      <h3>Next check</h3>
      <p>
        {output.follow_up.observation}
        {output.follow_up.when ? ` (${formatTimestamp(output.follow_up.when)})` : ""}
      </p>

      <PowerContextBlock summary={data.summary} />

      <p className="provenance">
        Provider mode: {data.provider_mode ?? "unknown"}, model: {data.model_id ?? "unknown"},
        prompt version: {data.prompt_version}
      </p>
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
}: {
  outcome: OutcomeResult | null;
  history: OutcomeHistoryEntry[];
  verificationHistory: VerificationHistoryEntry[];
  replayAt: string | null;
  unit: string | null;
  error: string | null;
  loading: boolean;
  verification: VerificationResult | null;
}) {
  if (!outcome && !error) return <p role="status">Loading outcome…</p>;
  if (!outcome) {
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
      <h3>History</h3>
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
    </div>
  );
}

function EvidenceTimelineSection({ entries }: { entries: EvidenceTimelineEntry[] }) {
  if (entries.length === 0) return <p>No evidence timeline entries yet.</p>;
  return (
    <ol className="evidence-timeline">
      {entries.map((entry) => (
        <li key={entry.kind} className="evidence-timeline-entry">
          <p className="evidence-timeline-label">{entry.label}</p>
          {entry.corroboration_only && <p className="corroboration-only">Corroboration only</p>}
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
        </li>
      ))}
    </ol>
  );
}

function SourceCard({ status }: { status: SourceStatus }) {
  const missing = status.availability === "missing" || status.newest_observed_at === null;
  return (
    <article className={`card availability-${status.availability}`} aria-label={`${status.source} source`}>
      <h3 className="card-title">{status.source}</h3>
      <p className="availability">
        <span className="dot" aria-hidden="true" />
        <span>
          Status: <strong>{AVAILABILITY_LABEL[status.availability]}</strong>
        </span>
      </p>
      <dl className="card-facts">
        <div>
          <dt>Records</dt>
          <dd>{missing ? "No reading" : status.record_count}</dd>
        </div>
        <div>
          <dt>Newest observed</dt>
          <dd>{formatTimestamp(status.newest_observed_at)}</dd>
        </div>
        <div>
          <dt>Age at evaluation time</dt>
          <dd>{formatAge(status.age_s)}</dd>
        </div>
      </dl>
      {(status.missing_count ?? 0) > 0 && (
        <p className="missing-readings">Missing readings: {status.missing_count}</p>
      )}
      {status.source === "weather" && !missing && (
        <p className="forecast-note">Forecast, not an on-property measurement.</p>
      )}
      {status.notes.length > 0 && (
        <ul className="notes">
          {status.notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      )}
    </article>
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
      )}
    </>
  );
}

const NOTIFICATION_AUDIENCE_LABEL: Record<NotificationAudience, string> = {
  homeowner: "Homeowner",
  property_manager: "Property manager",
  hvac_company: "HVAC company",
};

const REFUSAL_REASON_LABEL: Record<string, string> = {
  manager_not_authorized: "property manager not authorized",
  manager_hvac_not_authorized: "manager has not authorized HVAC contact",
};

function refusalReasonInWords(notification: Notification): string {
  const reason = notification.refusal_reason ?? notification.reason ?? "not authorized";
  return REFUSAL_REASON_LABEL[reason] ?? reason.replace(/_/g, " ");
}

function notificationStateInWords(notification: Notification): string {
  if (notification.state === "refused") return `Refused: ${refusalReasonInWords(notification)}`;
  if (notification.state === "simulated_delivered") return "Simulated delivery";
  if (notification.state === "queued") return "Simulated delivery";
  return notification.state.replace(/_/g, " ");
}

function NotificationsSection({
  notifications,
  error,
  onAck,
  ackingId,
}: {
  notifications: Notification[];
  error: string | null;
  onAck: (notification: Notification) => void;
  ackingId: string | null;
}) {
  if (error) {
    return (
      <p role="alert" className="error">
        Notifications not reachable
      </p>
    );
  }
  if (notifications.length === 0)
    return (
      <div className="notification-cards" aria-live="polite">
        <p>No notifications yet.</p>
      </div>
    );
  return (
    <div className="notification-cards" aria-live="polite">
      {notifications.map((notification) => {
        const audienceLabel =
          NOTIFICATION_AUDIENCE_LABEL[notification.audience] ?? notification.audience;
        const acks = notification.acks ?? [];
        const ack = acks.length > 0 ? acks[acks.length - 1] : null;
        return (
          <article
            key={notification.id}
            className="notification-card"
            aria-label={`${audienceLabel} notification`}
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
              {notification.whatsapp?.state === "delivered_to_test_number"
                ? "Sent to the owner's test number on WhatsApp (stands in for the HVAC company)"
                : "Simulated, no message was sent"}
            </p>
            <PayloadFacts payload={notification.payload} />
            {ack ? (
              <p className="notification-ack">
                Acknowledged, not resolved —{" "}
                <time dateTime={ack.acknowledged_at}>{formatTimestamp(ack.acknowledged_at)}</time>
              </p>
            ) : notification.audience === "property_manager" &&
              notification.state === "simulated_delivered" ? (
              <button
                type="button"
                onClick={() => onAck(notification)}
                disabled={ackingId === notification.id}
              >
                Acknowledge (simulated)
              </button>
            ) : null}
          </article>
        );
      })}
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
}: {
  verification: VerificationResult | null;
  targetTemp: number | null;
  targetUnit: string | null;
  verifiedFacts: string[];
}) {
  if (!verification || verification.stage !== "arrival_met" || targetTemp === null) return null;
  const unit = targetUnit ?? "F";
  const tempLabel = `${formatTargetTemp(targetTemp)} ${unit}`;
  const factsSupport =
    verifiedFacts.length > 0 ||
    verification.reasons.some((reason) => reason.includes(tempLabel) || reason.includes(String(targetTemp)));
  if (!factsSupport && verification.supporting_ids.length === 0) return null;
  return (
    <article className="homeowner-update-card" aria-label="Homeowner update">
      <p className="homeowner-update">
        Your home reached and held {tempLabel} before you arrived
      </p>
      <p>
        Evaluation time:{" "}
        <time dateTime={verification.evaluated_at}>{formatTimestamp(verification.evaluated_at)}</time>
      </p>
    </article>
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
  "not-responding": ["outcome", "investigation"],
  arrival: ["outcome", "homeowner"],
  "evidence-timeline": ["evidence-timeline"],
};

const KEY_CAPTIONS: Record<string, string> = {
  "k-plan": "Replay time: 9:20 AM ET",
  "k-trip": "Replay time: 9:20 AM ET",
  "k-location": "Replay time: 2:06 PM ET",
  "k-at-risk": "Replay time: 4:31 PM ET",
  "k-help": "Replay time: 4:52 PM ET",
  "k-ack": "Replay time: 4:52 PM ET",
  "k-restored": "Replay time: 6:21 PM ET",
  "k-warming": "Replay time: 6:51 PM ET",
  "k-not-yet": "Replay time: 7:51 PM ET",
  "k-verified": "Replay time: 8:21 PM ET",
  "k-arrival": "Replay time: 9:01 PM ET",
  "k-report": "Replay time: 8:46 PM ET",
  "k-home": "Replay time: 9:01 PM ET",
};

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
  const [verificationHistory, setVerificationHistory] = useState<VerificationHistoryEntry[]>([]);
  const [events, setEvents] = useState<ScenarioEvent[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [notificationsError, setNotificationsError] = useState<string | null>(null);
  const [ackingId, setAckingId] = useState<string | null>(null);
  const [followUpTargetTemp, setFollowUpTargetTemp] = useState<number | null>(null);
  const [selectedAt, setSelectedAt] = useState<string>(REPLAY_START_AT);
  const [livePower, setLivePower] = useState<LivePowerResponse | null>(null);
  const [sourcesLoading, setSourcesLoading] = useState(false);
  const sourcesTokenRef = useRef(0);
  const contextTokenRef = useRef(0);
  const investigationTokenRef = useRef(0);
  const replayTokenRef = useRef(0);
  const eventsTokenRef = useRef(0);

  useEffect(() => {
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
  }, [scenario, selectedAt]);

  useEffect(() => {
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
  }, [scenario, selectedAt]);

  useEffect(() => {
    const token = ++investigationTokenRef.current;
    const controller = new AbortController();
    const search = new URLSearchParams(window.location.search);
    const startAt = search.get("e2e_at") ?? startAtForScenario(scenario);
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
    setEvents([]);
    setNotifications([]);
    setNotificationsError(null);
    setFollowUpTargetTemp(null);
    setReplayAt(null);
    createInvestigation(scenario, startAt, { signal: controller.signal, queryExtra })
      .then((response) => {
        if (token !== investigationTokenRef.current) return;
        if (response.scenario !== scenario) return;
        setCreatedInvestigation(response);
        setInvestigationId(response.investigation_id);
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
        fetchFollowUp(response.investigation_id, startAt)
          .then((followUp) => {
            if (token !== investigationTokenRef.current) return;
            if (followUp.scenario !== scenario) return;
            setOutcome(followUp.outcome);
            setHistory(followUp.history);
            setVerification(followUp.verification ?? null);
            setEvidenceTimeline(followUp.evidence_timeline ?? []);
            setVerificationHistory(followUp.verification_history ?? []);
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
  }, [scenario]);

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
    let live = true;
    fetchLivePower().then((response) => {
      if (live) setLivePower(response);
    });
    return () => {
      live = false;
    };
  }, []);

  function handleScenarioChange(nextScenario: string) {
    replayTokenRef.current += 1;
    investigationTokenRef.current += 1;
    sourcesTokenRef.current += 1;
    contextTokenRef.current += 1;
    setContextData(null);
    setScenario(nextScenario);
    setSelectedAt(startAtForScenario(nextScenario));
    setSourcesLoading(true);
  }

  function handleReplayTime(at: string) {
    if (!investigationId) return;
    const token = ++replayTokenRef.current;
    setSelectedAt(at);
    setReplayLoading(true);
    setReplayError(null);
    fetchFollowUp(investigationId, at)
      .then((response) => {
        if (token !== replayTokenRef.current) return;
        if (response.scenario !== scenario) return;
        if (response.at && Date.parse(response.at) !== Date.parse(at)) return;
        setOutcome(response.outcome);
        setHistory(response.history);
        setVerification(response.verification ?? null);
        setEvidenceTimeline(response.evidence_timeline ?? []);
        setVerificationHistory(response.verification_history ?? []);
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

  function handleAck(notification: Notification) {
    setAckingId(notification.id);
    ackNotification(notification.id, "property_manager", replayAt ?? undefined)
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

  const verifiedFacts = createdInvestigation?.investigation?.output?.verified_facts ?? [];

  const displayInvestigation = createdInvestigation
    ? ({
        ...createdInvestigation.investigation,
        data_mode: "synthetic",
        evaluated_at: createdInvestigation.investigation.evaluated_at,
      } as unknown as InvestigationResponse)
    : null;

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

  return (
    <div className={`page${inset && insetPanels.length ? ` inset-active inset-${inset}` : ""}${keyCaption ? ` key-active key-${keyName}` : ""}`}>
      <section className="demo-controls" aria-label="Demo controls">
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
          {(scenario === VIDEO_SCENARIO ? VIDEO_REPLAY_TIMES : REPLAY_TIMES).map((time) => (
            <button
              key={time.at}
              type="button"
              onClick={() => handleReplayTime(time.at)}
              disabled={!investigationId}
              aria-pressed={selectedAt === time.at}
              aria-label={`Replay to ${time.label}`}
            >
              {time.label}
            </button>
          ))}
        </div>
      </section>
      <main>
      {data && (
        <p className="banner" role="status">
          {data.data_mode.toUpperCase()} DATA - demo scenario, not a real home{" "}
          <span className="banner-mode">(data mode: {data.data_mode})</span>
        </p>
      )}

      <header>
        <h1>Will my property be ready when I arrive, and if something looks wrong, who should respond?</h1>
        {data && (
          <p className="eval-time">
            Scenario evaluation time: <time dateTime={data.at}>{formatTimestamp(data.at)}</time>
          </p>
        )}
      </header>

      <section aria-labelledby="confirmed-plan-heading" className={insetClass("plan")}>
        <h2 id="confirmed-plan-heading">Confirmed plan and permissions</h2>
        <ConfirmedPlanSection data={contextData} error={contextError} />
      </section>

      <section aria-labelledby="investigation-heading" className={insetClass("investigation")}>
        <h2 id="investigation-heading">Investigation</h2>
        <InvestigationSection data={displayInvestigation} error={investigationError} created={createdInvestigation} replayAt={selectedAt} />
      </section>

      <section aria-labelledby="outcome-heading" className={insetClass("outcome")}>
        <h2 id="outcome-heading">Outcome</h2>
        <OutcomeSection
          outcome={outcome}
          history={history}
          verificationHistory={verificationHistory}
          replayAt={replayAt}
          unit={followUpUnit}
          error={replayError}
          loading={replayLoading}
          verification={verification}
        />
      </section>

      <section aria-labelledby="evidence-timeline-heading" className={insetClass("evidence-timeline")}>
        <h2 id="evidence-timeline-heading">Evidence timeline</h2>
        <EvidenceTimelineSection entries={evidenceTimeline} />
      </section>

      <section aria-labelledby="notifications-heading" className={insetClass("notifications")}>
        <h2 id="notifications-heading">Notifications (simulated delivery)</h2>
        <NotificationsSection
          notifications={visibleNotifications}
          error={notificationsError}
          onAck={handleAck}
          ackingId={ackingId}
        />
      </section>

      <section aria-labelledby="homeowner-update-heading" className={insetClass("homeowner")}>
        <h2 id="homeowner-update-heading">Homeowner update</h2>
        <HomeownerUpdateCard
          verification={verification}
          targetTemp={followUpTargetTemp}
          targetUnit={followUpUnit}
          verifiedFacts={verifiedFacts}
        />
      </section>

      <section aria-labelledby="timeline-heading" className={insetClass("timeline")}>
        <h2 id="timeline-heading">Simulated timeline</h2>
        <SimulatedTimeline events={events} replayAt={replayAt} />
      </section>

      <section aria-labelledby="evidence-heading" className={insetClass("evidence")}>
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
          <div className="cards">
            {SOURCE_ORDER.map((source) => {
              const status = data.sources.find((s) => s.source === source);
              return status ? <SourceCard key={source} status={status} /> : null;
            })}
          </div>
        )}
      </section>
      {livePower && livePower.status === "ok" && (
        <section aria-labelledby="live-power-heading">
          <h2 id="live-power-heading">Your real home, right now (live, read-only, Emporia Vue)</h2>
          <LivePowerPanel data={livePower} />
        </section>
      )}
      </main>
      {keyCaption && <p className="key-caption">{keyCaption}</p>}
    </div>
  );
}
