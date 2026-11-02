# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A single-file Python CLI (`generate.py`) that uses `build123d` to produce STLs.
All geometry is parameterized via named constants at the top of `generate.py`; a
subset is exposed via argparse — see `--help`. Three components: `m` and `s`
(magnetic letter coins) and `magnet-test` (graded press-fit test strip). STLs
are written to CWD as `letter-coins-<component>.stl`; `--all` exports all three.

This repo was scaffolded by Partwright; the real geometry is implemented in
`build_part` (dispatching to `_build_coin` / `_build_magnet_test`).

## Design documents

`DESIGN_BRIEF.md` is the design record — what the part is, every parameter with
its default and meaning, and the constraints that matter. `BUILD_PLAN.md` is the
implementation handoff — the concrete geometry recipe. **Both are written by the
design interview before any geometry exists.** Work from `BUILD_PLAN.md` and
treat `DESIGN_BRIEF.md` as the authority on intent.

Express derived dimensions as live Python, never as pre-computed numbers:

```python
SOCKET_BORE_MM = VAC_TUBE_OD_MM + 2 * SOCKET_CLEARANCE_MM   # yes
SOCKET_BORE_MM = 40.0                                       # no
```

A frozen literal makes the part look parametric while quietly ignoring the CLI
flag it depends on — the printed part then refuses to change when the maker
tunes that flag.

## Visual verification loop

This repo can render itself, so **verify geometry visually before declaring a
change done, and show the user the rendered preview.** For every geometry change:

1. Read `BUILD_PLAN.md` and `DESIGN_BRIEF.md` for the intended geometry, and
   check `reference/` for sketches (see below).
2. Implement or edit `build_part` in `generate.py`.
3. Run `.venv/bin/python generate.py` — exports the STL and surfaces build errors.
4. Run `.venv/bin/python preview.py --all` — renders `preview.png` (the `m`
   coin), `preview-s.png` and `preview-magnet-test.png`, each a 2x3 contact
   sheet (isometric, top, bottom, front, right, XZ section).
5. **`Read` each preview PNG** and check it against the plan: right overall shape,
   +Z up, floor on z = 0, centered in X/Y, features placed correctly, no gaps
   from Boolean issues.
6. If it is wrong, fix `build_part` and repeat from step 3. If it is right,
   **show the user `preview.png`** and summarize what changed.

`preview.py` imports `build_part` from `generate.py` and calls it with no
arguments, so **`build_part` must always be callable with no arguments** (every
parameter keeps a default). The renderer is installed by
`uv pip install -r requirements.txt`. For a multi-component part, extend
`preview.py` to render each component (loop over them, or fuse for a combined view).

## Multi-component parts

When `DESIGN_BRIEF.md` declares more than one `component`, `generate.py` carries
a `COMPONENTS` tuple and the build/check/export contract is per-component:

- **`build_part` return contract.** `build_part(component=...)` dispatches to the
  named component's geometry. Called with **no arguments** it returns the **first**
  component (`COMPONENTS[0]`), so `preview.py` and the out-of-the-box run still
  work. Keep this shape when you implement the real geometry: one builder per
  component, dispatched by name, no-arg still returning the first.
- **STL export.** `--component <name>` builds and exports a single component to
  `<project>-<component>.stl`; `--all` exports every component, each to its own
  per-component filename, in one run. An explicit `--output` applies only when a
  single component is exported. (A single-component part still exports to
  `<project>.stl` with no `--component` flag.)
- **`check_part` iterates components.** It builds each component, prints its
  bounding box and solid count, and asserts **each** component is a single
  watertight solid — so a genuine multi-piece part no longer trips the
  "expected exactly one solid" check. Fill in the per-component expected-dimension
  map to turn the readout into a hard assert.

## Coordinate system

Right-handed; origin at the center of the footprint, back face on the build
plate at z = 0.

- **+X** — coin: rightward as the letter is read from above. Test strip: along
  the bar, from the tightest pocket (−X, rounded end) to the loosest (+X, square
  end).
- **+Y** — coin: "up" for the letter as read from above. Test strip: across the
  bar's width.
- **+Z** — up from the back face (magnet pocket opening; sits on the build plate
  and against the whiteboard) toward the top face / top of the letter.

All components (`m`, `s`, `magnet-test`) are centered in X and Y; floor on
z = 0. Modelled in printed orientation — no rotation before export.

## Python environment caveat

The README uses `uv` because some local Homebrew Python installs have a broken
`pyexpat` that makes `python -m venv` fail at `ensurepip`. `uv` sidesteps this
by managing its own Python. Don't restructure `generate.py` to "work around" a
broken interpreter — use `uv` to get a clean Python 3.12.

## Code style

Python is formatted with [black](https://black.readthedocs.io/) (pinned in
`requirements-dev.txt`). Black is **not** in the runtime venv, so install the dev
deps once before formatting:

```sh
uv pip install -r requirements-dev.txt
```

Then run `.venv/bin/black generate.py` after edits — black is the source of
truth, so don't hand-align constants or wrap lines manually.

## Boolean-robustness conventions

OCCT booleans are flaky when an operation must resolve two coincident faces, and
the artifacts only show up after STL export. When you add a feature that cuts or
fuses to a face of the parent solid, give the cutter a small overshoot (a
`_FACE_OVERLAP_MM`-style tab) so the Boolean never resolves a coincident face.

Fillets need the same care on edge selection. A single scalar radius usually
cannot be applied to a whole edge set at once — at a tight concave corner the
requested radius exceeds the available room and OCCT raises
`ValueError: Failed creating a fillet`. Select the edges deliberately (filter by
position or orientation, e.g. only the four vertical outer corners) rather than
filleting every edge, and keep the radius within what the geometry allows.

## Reference sketches

The `reference/` folder holds design-intent drawings — SVGs from
`partwright sketch` and reference photos. **Look there before implementing
geometry** and reconcile `build_part` against what you find. Precise-mode SVGs
carry a real millimeter scale in their metadata; treat those dimensions as
authoritative.

## Non-obvious geometry decisions

- **Font: Arial, bold** (`LETTER_FONT` / `LETTER_FONT_STYLE`). The build123d
  default font name is "Arial"; on macOS OCCT resolves it to
  `/System/Library/Fonts/Supplemental/Arial Bold.ttf`. Both M and S come out as
  a single face each. If the font is missing (e.g. Linux), OCCT silently
  substitutes another font and prints a `Font_FontMgr` warning — re-check the
  preview there.
- **Letter scaling by measured bbox.** `font_size` is not cap height.
  `_letter_sketch` builds the glyph once at `font_size = letter_height`,
  measures its Y extent and rebuilds at `letter_height**2 / measured`, so the
  glyph's Y extent (including the S's overshoot) is exactly `letter_height`.
  The glyph is then centered on its own bounding box, not the font baseline.
  At defaults M is 13.52 × 14.0 mm, S is 11.00 × 14.0 mm.
- **Builders recompute derived dimensions** via `_derived(**params)` from their
  keyword arguments; the module-level derived constants are documentation of
  the defaults only. Don't read them inside a builder, or CLI flags go dead.
- **Strip outline** is one sketch: a circle of radius `strip_width / 2`
  concentric with pocket 0 plus a rectangle from pocket 0's center to the +X
  end, extruded once. Because `strip_width / 2 = pocket_max / 2 + wall`, the
  rounded end lands exactly at −`strip_length / 2`.
- **Pocket count check** counts distinct cylinder axes with radius ≤ the largest
  pocket radius; the coin rim and the strip's rounded end are always larger by
  at least a wall, so they're excluded.
- **Preview is a 2x3 sheet** (isometric, top, bottom look-through, front, right,
  XZ section at y = 0). Blind pockets are invisible from the top, so the bottom
  plan and the section panel are what verify pocket placement and depth.
- **requirements.txt pins `ocpsvg==0.5.0`**: build123d 0.9.1 would otherwise
  pull ocpsvg 0.7, which needs a newer OCP and makes `import build123d` fail.
