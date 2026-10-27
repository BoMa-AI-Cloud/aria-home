Model: muse-wonder-1.0
Turns: 47

The e2e failure is cross-run DB pollution: the shared `instance` DB already held an HVAC notification created at 21:01, so a correct 16:52 projection excludes it. Isolating the e2e DB (as the record config already does) makes the sequential replay create it at 16:52.
