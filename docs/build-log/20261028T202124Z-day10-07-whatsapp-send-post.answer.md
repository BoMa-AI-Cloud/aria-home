Model: muse-spark-1.3
Turns: 60

Done. GET never sends; delivery is an explicit POST.

**Files changed**
- `backend/aria_home/app.py` — removed `attempt_hvac_whatsapp_delivery` from `GET /api/follow-ups/<id>`; added `GET /api/whatsapp/status` (read-only, `{configured}` only) and `POST /api/notifications/<id>/whatsapp` (404 unknown, 409 non-HVAC / `not_configured` / `not_yet_visible`, returns recorded delivery state)
- `backend/aria_home/whatsapp.py` — audit generation: `idempotency` mentions repeated GETs; new `trigger` (POST-only, GET never sends) and `status` keys
- `backend/tests/test_audit3_whatsapp.py` — rewritten to new contract: repeated GETs assert zero fake-HTTP calls with flag on; POST sends once; second POST no re-send; 409 not-configured/wrong-audience/not-yet-visible; 404 unknown; status endpoint leaks no values
- `docs/whatsapp-audit.json` — regenerated (new idempotency/trigger/status)
- `frontend/src/api.ts` — `fetchWhatsappStatus`, `sendHvacWhatsapp`, response types
- `frontend/src/App.tsx` — HVAC card shows "Send to my test phone (WhatsApp)" only when status says configured; manual POST, never automatic
- `README.md`, `docs/inference-idempotency.md`, `SECURITY.md` — POST-only trigger, GET read-only, button hidden when unconfigured

**Command output (real lines)**
- `cd backend && python -m pytest -q` (first run, before audit JSON regen): `1 failed, 371 passed in 43.18s` — only `test_whatsapp_audit_matches_code`, differing on the new idempotency/trigger/status text
- `cd backend && python -m pytest -q` (final): `372 passed in 40.25s`
- `cd ../frontend && npm run typecheck`: `> aria-home-frontend@0.1.0 typecheck` / `> tsc --noEmit` — no errors
- `npm run test:e2e`: `32 passed (1.3m)` (e2e log shows `GET /api/whatsapp/status HTTP/1.1" 200` alongside the other reads; button hidden since e2e backend has no WhatsApp env)
