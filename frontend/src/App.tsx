import { useEffect, useState } from "react";
import {
  fetchSources,
  type Availability,
  type SourceKind,
  type SourceStatus,
  type SourcesResponse,
} from "./api";
import "./index.css";

const SOURCE_ORDER: SourceKind[] = ["calendar", "thermostat", "electrical", "weather"];

const AVAILABILITY_LABEL: Record<Availability, string> = {
  available: "Available",
  missing: "Missing",
  stale: "Stale",
  invalid: "Invalid",
  conflicting: "Conflicting",
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

  useEffect(() => {
    let cancelled = false;
    fetchSources()
      .then((response) => {
        if (!cancelled) setData(response);
      })
      .catch(() => {
        if (!cancelled) setError("Backend not reachable");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main className="page">
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
        <p>Coming in Day 3: ARIA&apos;s explanation of the evidence.</p>
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
