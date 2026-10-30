# Synthetic care-story camera fixtures

All six images are SYNTHETIC: generated on 2026-10-29 by muse-image-1.0 (Meta Model API) to look like frames from fixed
home cameras (ceiling-corner, wide-angle, infrared at night). No real home or camera is shown. Each `*.sam.txt` is the
recorded raw sam-3.1 response for that image and phrase, captured the same day; tests replay them and never call the API.

| Image | Phrase | sam-3.1 objects | Correct? |
|---|---|---|---|
| care-v1-window-frost | frost | 0 | missed (frost on every pane) |
| care-v2-furnace-off | indicator light | 0 | unclear (small indicator) |
| care-v3-thermostat-blank | blank display | 1 | yes |
| care-v4-pipe-frost | frost | 0 | missed |
| care-v5-dry-floor | water puddle | 0 | yes (negative control) |
| care-v6-warm-morning | frost | 0 | yes (no frost present) |
