Meta AI (meta.ai web chat, account saf_integration) returned code blocks for release_version(), the health() change, backend/tests/test_version_stamp.py, the HealthResponse field, the version state line, VersionLine and a .version-line CSS rule.

Used as given except: the bare `except Exception` around the file read was narrowed to `except OSError`; the CSS went into frontend/src/index.css (there is no App.css). The operator added: the VersionLine placements (public landing and app footer), the two exact-health tests updated to pop `version`, two browser tests, the release-process stage 12 and README text, the .gitignore and .env.example lines, and removal of the landed xfail in test_process_laws.py.

Why the web chat: the Model API key returned 402 "Billing verification failed" for every worker job from 20:20Z on 2026-10-29; Brad said "use meta ai if the api key is donzo".

Operator retest: red-proof (format check removed -> test_invalid_env_value_ignored failed with AssertionError; restored -> 5 passed); backend 552 passed; typecheck and build pass; the two version browser tests pass in both suites.
