# 🏮 Lantern Quay 燈港 · v1 sample

Rooftop sniper sample set in an invented canal city. Climb a perch, find the mark in the crowd, fire while the bell tower rings, dive into the canal. Built on the Canal District world pipeline (copied from `canal-district-local`, stage 5 added in `scripts/lib/quay.py` + `lq_layout.py`).

Play: https://icomppower.github.io/lantern-quay/ · Spec and status live in Notion.

```sh
npm install && npm run dev                 # play locally
npm run build && node tests/gates.mjs      # V1 V2 V3 gates + V5 shots (Playwright Chromium)
node tools/serve.mjs 8765                  # then open ?bench=1&dpr=1080p in Safari for V4
scripts/run_step.sh LQ1 --stage 5 --out milestones/LQ1 && \
  blender -b milestones/LQ1.blend --python scripts/export_glb.py   # rebuild public/world/
```

Controls: WASD move · Shift run / hold breath · C crouch · right-click or Z scope · Q 4×/10× · click fire · E ladder · F dive.
