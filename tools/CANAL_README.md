# Canal District

An original, explorable 3D canal district (about 40 × 30 m) built from scratch with Blender Python
scripts, plus a single-file three.js viewer. The terrace house, stair, plaza, canal, bridge and
airship are all generated geometry; no asset libraries are used.

## Run the viewer
```sh
node viewer/serve.mjs            # http://localhost:8765/
```
- Orbit: drag to rotate, scroll to zoom.
- Walk: press **W** or the Walk button, click to look around, WASD or arrows to move, Shift to run.
- Test hooks:
  - `?bench=1&secs=30` logs FPS and load time to `reports/`.
  - `?test=walk` walks every path at 1.7 m eye height and logs clipping and floating to `reports/`.
  - `?cam=ref|hero|bridge|east|top` matches a Blender camera.

Any static server works for viewing. The bundled one also accepts the test reports.

## Rebuild from scratch
```sh
python3 scripts/gen_textures.py                                   # tileable textures -> materials/textures
scripts/run_step.sh M4 --stage 4 --render ref,bridge,east,top --out milestones/M4 --hero
blender -b milestones/M4.blend --python scripts/export_glb.py     # -> viewer/canal_district.glb + scene_meta.json
python3 scripts/compare.py milestones/M4_hero.png out.png         # reference vs render, stacked
```
`--stage 2` builds the canal and bridge section, `3` the full district, and `4` adds the airship, scenery and final light.
`run_step.sh` runs each step in a fresh Blender process and appends peak memory to `milestones/memory.log`.

## Layout
| Path | What |
|---|---|
| `scripts/build.py` | Entry point (stages, renders, hero) |
| `scripts/lib/` | `core` (materials, mesh builder, instancing), `layout` (dimensions, paths, cameras), `arch` (facades, buildings), `site` (ground, canal, terrace, stair, bridge), `assets`, `veg`, `airship`, `scenery`, `sky` |
| `materials/textures/` | Generated 1K/512 textures; `baked/` holds the tinted copies made for the GLB |
| `milestones/` | `.blend` and preview renders per milestone, `memory.log`, run logs |
| `viewer/` | `index.html`, `canal_district.glb`, `scene_meta.json`, vendored three.js 0.185 (`lib/`) |
| `reports/` | Safari and Chromium benchmark and walk-test JSON |

## Conventions
- 1 unit = 1 m. Blender is Z-up, with the origin at the district's SW corner (X east, Y north).
- The GLB is glTF **Y-up**: Blender (x, y, z) maps to (x, z, −y).
- Blender is 5.2.1 LTS (`/Applications/Blender.app`), rendered with Cycles on Metal.
- Metal kernel optimisation is set to OFF per session, because specialised-kernel compiles hung once.

See `REPORT.md` for performance, export limitations and kill-gate results. Milestone verdicts are in `BUILD_LOG.md`.
