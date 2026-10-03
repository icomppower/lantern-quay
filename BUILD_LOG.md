# Build log — v1 sample (2026-10-03)

| Gate | Verdict | Evidence |
|---|---|---|
| World | PASS | Stage 5 (`scripts/lib/quay.py`, `lq_layout.py`) grows the Canal District to ~150 × 100 m: 31 houses + 2 perch roofs + bell tower (16 m deck, ~26 m with dome), 2 new humpback bridges, instanced town fill. Blender build 8 s, peak 0.38 GB; export peak 3.7 GB; `public/world/world.glb` 37.4 MB. |
| V1 reach + sightlines | PASS | `reports/v1.json`: spawn → perch A 114 m / 22.8 s, → perch B 107 m / 21.5 s, → tower 67 m / 13.4 s, all ladders climbed. Target clear-view per loop: Toll Collector A 32 s / B 31.4 s; Bookkeeper A 8.8 s / B 8.6 s (awning gusts). |
| V2 ballistics | PASS | `reports/v2.json`: 0.5 m target hit at 60 m and 120 m with drop + 3.7 m/s crosswind holdover; 120 m without holdover misses; café awning blocks when down, target hit when up. |
| V3 contracts | PASS | `reports/v3.json`, `v3_B.json`: both contracts completed from both perches (1 masked shot each, 61–74 m, then dive escape); a civilian hit fails the contract. |
| V4 perf | PASS | `reports/safari_bench2.json`: Safari 26.6, 10× scope on the bridge, canvas 1920×1232: avg 59.8 fps, p95 50 fps (20 ms), 561 draws; load 0.8 s from localhost. Live: GLB cold download 1.45 s from Pages → ~2.3 s first load (estimated: Safari blocks the live page reporting to localhost). |
| V5 shots | PASS | `shots/plaza_street.png`, `scope_bridge.png`, `perch_overview.png`, `title.png` (1920×1080, Chromium). |
