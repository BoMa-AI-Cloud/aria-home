Model: muse-wonder-1.0
Turns: 60

Changes:
- `frontend/src/api.ts` — `Notification`/`NotificationAck`/`NotificationsResponse`/`AckNotificationResponse` types, `notifications` on create/follow-up responses, `fetchNotifications()` and `ackNotification()`.
- `frontend/src/App.tsx` — “Notifications (simulated delivery)” panel (audience/state in words, created time, exact payload fields as labeled list, “Simulated, no message was sent” on every card), “Acknowledge (simulated)” on delivered manager cards showing “Acknowledged, not resolved” with time without touching Outcome, replay-time visibility filter for cards, `16:52` video replay button, and the homeowner update card at `arrival_met`: “Your home reached and held 68 F before you arrived” + evaluation time, derived from verification + follow-up target/verified facts.
- `frontend/src/index.css` — notification/homeowner-update card styles.
- `frontend/e2e/app.spec.ts` — new test covering 16:31 manager/refused-HVAC, 16:52 scoped HVAC payload, ack vs. unchanged Outcome headline, 21:01 homeowner update, and “Simulated” on every card.
- No backend changes.

REAL output lines:
- `198 passed in 5.15s` (`cd backend && python -m pytest -q`)
- `> tsc --noEmit` (typecheck, exit clean)
- `✓ built in 836ms` / `assets/index-7yV1ATiR.js 245.70 kB` (`npm run build`)
- `4 passed (10.2s)` (`npm run test:e2e`), and `4 passed (10.5s)` on a repeat run
