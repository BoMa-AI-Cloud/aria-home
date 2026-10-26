ARIA Home, small Day 4 addition (approved by Brad). No live calls, no installs, no network, no
git, NO helper scripts. Do not end your turn until `cd backend && python -m pytest -q` passes.
Read only backend/aria_home/store.py, backend/aria_home/app.py and backend/tests/test_store.py.

The follow-up API keeps only the latest status. Add an outcome history:
1. store.py: a table outcome_events (investigation_id, evaluated_at, status, sample_count, note,
   UNIQUE(investigation_id, evaluated_at)); record_outcome inserts one event (insert-or-ignore, so
   re-evaluating at the same time adds nothing) in addition to updating the follow-up; add
   list_outcomes(investigation_id) returning events in evaluated_at order.
2. app.py: GET /api/follow-ups/<id> also returns "history": the list of events.
3. Tests: for demo_recovery_v1 created at 18:00, GET at 19:00 then 20:31 returns two history
   entries [warming_observed, target_reached]; repeating the 20:31 GET keeps two; a new Store on
   the same file still lists both (restart). Use a tmp_path database via ARIA_HOME_DB_PATH.
Final answer: the change and the REAL final pytest line.

