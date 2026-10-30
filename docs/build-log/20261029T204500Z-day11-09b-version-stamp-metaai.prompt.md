You are writing code for ARIA Home (Python 3 Flask backend + React/TypeScript frontend). Reply ONLY with complete code blocks I can paste, each headed by the file path and exactly where it goes. No prose beyond one line per block.

TASK: report the running version.
GET /api/health adds "version": {"commit": <value>, "source": <how found>}.
- commit from env var ARIA_HOME_RELEASE_COMMIT (source "env"), if set and non-empty after strip;
- else from file backend/RELEASE_COMMIT (first line, stripped; source "file");
- else {"commit": "unknown", "source": "not stamped"}.
Never shell out to git, never guess. Only accept values matching ^[0-9a-fA-F]{7,40}$; anything else -> treat as absent (so no other env data can leak). Health must stay 200.

CURRENT backend/aria_home/app.py (inside create_app; `Path`, `os`, `jsonify`, `timedelta` already imported; this file lives at backend/aria_home/app.py):
    @app.get("/api/health")
    def health():
        db_marker = Path(os.environ.get("ARIA_HOME_DB_PATH") or "").name or None
        return jsonify({"status": "ok", "service": "aria-home-backend", "data_mode": "synthetic", "scenario": scenario.manifest.id, "at": (scenario.manifest.start + timedelta(hours=3)).isoformat(), "timezone": scenario.manifest.timezone, "db_marker": db_marker, "public_demo": public})

Give: (1) a module-level function `release_version(base_dir: Path | None = None) -> dict` for app.py (base_dir defaults to the backend directory, i.e. Path(__file__).resolve().parent.parent), (2) the new health() body adding "version": release_version().

(3) A new pytest file backend/tests/test_version_stamp.py using monkeypatch and tmp_path only (never os.environ directly): env value wins over file; file used when env unset (monkeypatch.delenv ARIA_HOME_RELEASE_COMMIT, pass base_dir=tmp_path); neither -> unknown/not stamped; invalid env value like "abc; SECRET=1" -> ignored; /api/health via `from aria_home.app import create_app; create_app().test_client()` returns 200 with version.commit equal to a monkeypatched env sha. A test must never write under the repo.

Frontend, frontend/src/api.ts has:
export interface HealthResponse {
  status: string;
  service: string;
  data_mode: DataMode;
  scenario: string;
  at: string;
  timezone: string;
  public_demo?: boolean;
}
(4) Add `version?: { commit: string; source: string };`.

frontend/src/App.tsx, in `export default function App()`, a useEffect calls fetchHealth().then((health) => {...}). (5) Give: a state line `const [version, setVersion] = useState<string | null>(null);`, the one line to add as the first statement inside `.then((health) => {` after `if (!live) return;` that sets setVersion(health.version?.commit ?? "unknown"), and a small component:
function VersionLine({ commit }: { commit: string | null }) -> renders <p className="version-line" data-testid="version-line">Version {short}</p> where short is the first 7 chars, or "unknown" for "unknown"; renders nothing when commit is null.
(6) a CSS rule for .version-line (small, muted, centered, margin 1rem 0).
