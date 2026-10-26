import { useEffect, useState } from "react";
import {
  createInvestigation,
  fetchFollowUp,
  fetchInvestigation,
  fetchSources,
  type Availability,
  type ContextFlags,
  type CreateInvestigationResponse,
  type InvestigationResponse,
  type InvestigationSummary,
  type OutcomeHistoryEntry,
  type OutcomeResult,
  type OutcomeStatus,
  type Readiness,
  type ReadinessResult,
  type SourceKind,
  type SourceStatus,
  type SourcesResponse,
} from "./api";
import "./index.css";

const SCENARIOS = [
  { id: "demo_v1", label: "No recovery" },
  { id: "demo_recovery_v1", label: "Manager visit, heat restored" },
  { id: "demo_no_followup_v1", label: "No follow-up readings" },
];

const REPLAY_START_AT = "2026-01-16T18:00:00-05:00";

const REPLAY_TIMES = [
  { label: "18:00", at: "2026-01-16T18:00:00-05:00" },
  { label: "18:30", at: "2026-01-16T18:30:00-05:00" },
  { label: "19:00", at: "2026-01-16T19:00:00-05:00" },
  { label: "20:31", at: "2026-01-16T20:31:00-05:00" },
];

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

function formatTimestamp(value: string | null): string {
  if (!value) return "No reading";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
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

function InvestigationSection({
  data,
  error,
  created,
}: {
  data: InvestigationResponse | null;
  error: string | null;
  created: CreateInvestigationResponse | null;
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

  if (data.status === "rejected" || data.status === "unavailable" || !data.output) {
    return (
      <>
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
  replayAt,
  unit,
  error,
  loading,
}: {
  outcome: OutcomeResult | null;
  history: OutcomeHistoryEntry[];
  replayAt: string | null;
  unit: string | null;
  error: string | null;
  loading: boolean;
}) {
  if (!outcome && !error) return <p role="status">Loading outcome…</p>;
  if (!outcome) {
    return (
      <p role="alert" className="error">
        Follow-up not reachable
      </p>
    );
  }
  const valueUnit = unit ? ` °${unit}` : "";
  return (
    <div className={`outcome outcome-${outcome.status}`}>
      {loading && <p role="status">Loading outcome…</p>}
      {error && (
        <p role="alert" className="error">
          Follow-up refresh failed
        </p>
      )}
      <p className="outcome-status">
        Status: <strong>{OUTCOME_LABEL[outcome.status]}</strong>
      </p>
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
      {history.length === 0 ? (
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

export default function App() {
  const [data, setData] = useState<SourcesResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [investigation, setInvestigation] = useState<InvestigationResponse | null>(null);
  const [createdInvestigation, setCreatedInvestigation] =
    useState<CreateInvestigationResponse | null>(null);
  const [investigationError, setInvestigationError] = useState<string | null>(null);
  const [scenario, setScenario] = useState<string>(SCENARIOS[0].id);
  const [investigationId, setInvestigationId] = useState<string | null>(null);
  const [outcome, setOutcome] = useState<OutcomeResult | null>(null);
  const [history, setHistory] = useState<OutcomeHistoryEntry[]>([]);
  const [followUpUnit, setFollowUpUnit] = useState<string | null>(null);
  const [replayAt, setReplayAt] = useState<string | null>(null);
  const [replayLoading, setReplayLoading] = useState(false);
  const [replayError, setReplayError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchSources()
      .then((response) => {
        if (!cancelled) setData(response);
      })
      .catch(() => {
        if (!cancelled) setError("Backend not reachable");
      });
    fetchInvestigation()
      .then((response) => {
        if (!cancelled) setInvestigation(response);
      })
      .catch(() => {
        if (!cancelled) setInvestigationError("Investigation not reachable");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setReplayLoading(true);
    setReplayError(null);
    createInvestigation(scenario, REPLAY_START_AT)
      .then((response) => {
        if (cancelled) return;
        setCreatedInvestigation(response);
        setInvestigationId(response.investigation_id);
        setOutcome(response.outcome);
        setHistory([]);
        setFollowUpUnit(
          typeof response.follow_up?.target_unit === "string"
            ? response.follow_up.target_unit
            : null,
        );
        setReplayAt(REPLAY_START_AT);
        setReplayLoading(false);
      })
      .catch(() => {
        if (cancelled) return;
        setInvestigationId(null);
        setReplayError("Follow-up not reachable");
        setReplayLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [scenario]);

  function handleReplayTime(at: string) {
    if (!investigationId) return;
    setReplayLoading(true);
    setReplayError(null);
    fetchFollowUp(investigationId, at)
      .then((response) => {
        setOutcome(response.outcome);
        setHistory(response.history);
        setReplayAt(at);
        setReplayLoading(false);
      })
      .catch(() => {
        setReplayError("Follow-up not reachable");
        setReplayLoading(false);
      });
  }

  return (
    <main className="page">
      <div className="demo-controls" role="group" aria-label="Demo controls">
        <p className="demo-controls-title">Demo controls (synthetic replay)</p>
        <label className="demo-scenario">
          Scenario{" "}
          <select
            aria-label="Scenario"
            value={scenario}
            onChange={(event) => setScenario(event.target.value)}
          >
            {SCENARIOS.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <div className="demo-times" role="group" aria-label="Replay time">
          {REPLAY_TIMES.map((time) => (
            <button
              key={time.at}
              type="button"
              onClick={() => handleReplayTime(time.at)}
              disabled={!investigationId || replayLoading}
              aria-pressed={replayAt === time.at}
            >
              {time.label}
            </button>
          ))}
        </div>
      </div>
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

      <section aria-labelledby="investigation-heading">
        <h2 id="investigation-heading">Investigation</h2>
        <InvestigationSection data={investigation} error={investigationError} created={createdInvestigation} />
      </section>

      <section aria-labelledby="outcome-heading">
        <h2 id="outcome-heading">Outcome</h2>
        <OutcomeSection
          outcome={outcome}
          history={history}
          replayAt={replayAt}
          unit={followUpUnit}
          error={replayError}
          loading={replayLoading}
        />
      </section>

      <section aria-labelledby="evidence-heading">
        <h2 id="evidence-heading">Evidence sources</h2>
        {!data && !error && <p role="status">Loading evidence…</p>}
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
    </main>
  );
}
