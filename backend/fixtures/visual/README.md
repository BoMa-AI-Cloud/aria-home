# Synthetic visual fixtures

All four images are SYNTHETIC: generated on 2026-10-28 by muse-image-1.0 through the Meta Model API from the
prompts in `<private-notes>/smoke/visual_probe.py` (water on a basement floor, frost on a copper pipe, a dry
basement floor, frost on a window). No real home is shown.

Each `*.sam.txt` is the recorded raw sam-3.1 response (Meta Model API, POST /v1/responses) for that image and the
phrase in `probe-results.json`, captured the same day. Tests replay these recordings; they never call the API.

Recorded outcome: water puddle found (1 object); frost on the pipe NOT found (0 objects, a false negative);
dry floor correctly empty (0); frost on the window found (4 objects).
