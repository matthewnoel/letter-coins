# Build Plan — letter-coins

The implementation handoff for the build agent. It turns `DESIGN_BRIEF.md` (the
*what*) into a concrete plan for `generate.py` (the *how*).

## Objective

`generate.py` builds three components, selected with `--component`:

- `m` — a coin with an embossed "M" (default / first component),
- `s` — a coin with an embossed "S",
- `magnet-test` — a bar of graded magnet pockets for tuning the press fit.

`--all` exports all three. Every component must build with default parameters
and emit a valid STL; `build_part()` with no arguments returns the `m` coin.

## Geometry approach

Right-handed; origin at the center of the footprint, back face on the build
plate at z = 0. Put this verbatim in the `generate.py` docstring and in
`CLAUDE.md`'s "Coordinate system" section.

- **+X** — coin: rightward as the letter is read from above. Test strip: along
  the bar, from the tightest pocket (−X, rounded end) to the loosest (+X, square
  end).
- **+Y** — coin: "up" for the letter as read from above. Test strip: across the
  bar's width.
- **+Z** — up from the back face (magnet pocket opening; sits on the build plate
  and against the whiteboard) toward the top face / top of the letter.

All components are centered in X and Y; floor on z = 0. Model in printed
orientation — no rotation before export.

### Shared helper: magnet pocket cutter

`_magnet_pocket(diameter, x=0.0)` → a `Cylinder` of `diameter`, spanning
z = −`_FACE_OVERLAP_MM` to z = `POCKET_DEPTH_MM`, centered at (x, 0). Used by
both the coins and the strip, so the pocket depth/roof are identical.

### `m` and `s` coins (`_build_coin(letter)`)

1. Body: `Cylinder(radius=COIN_DIAMETER_MM / 2, height=BODY_THICKNESS_MM)`,
   aligned so it spans z = 0 … `BODY_THICKNESS_MM`, centered on the Z axis.
2. Cut the magnet pocket: `_magnet_pocket(POCKET_DIAMETER_MM)` at the center.
3. Letter: build the glyph with build123d `Text(letter, font_size=...,
   font_style=FontStyle.BOLD)` (a sans-serif font; the default is fine — see
   Known risks). Scale it so the glyph's **Y extent equals `LETTER_HEIGHT_MM`**
   (`font_size` is not cap height — measure the glyph's bounding box and rescale,
   or compute font_size from a measured ratio). Center the glyph's own bounding
   box at X = Y = 0, upright when read from +Z with +Y as "up" (not mirrored).
4. Extrude the letter face from z = `BODY_THICKNESS_MM - _FACE_OVERLAP_MM` to
   z = `TOTAL_HEIGHT_MM` (i.e. extrude by `LETTER_EMBOSS_MM + _FACE_OVERLAP_MM`)
   and fuse it onto the body.
5. Result must be one solid. Letter is a component→letter map:
   `{"m": "M", "s": "S"}`.

### `magnet-test` strip (`_build_magnet_test()`)

1. Plan-view outline (XY), extruded from z = 0 to `BODY_THICKNESS_MM`: a
   rectangle `TEST_STRIP_LENGTH_MM` × `TEST_STRIP_WIDTH_MM` centered at the
   origin, **with its −X end fully rounded** (a semicircle of radius
   `TEST_STRIP_WIDTH_MM / 2`) and its +X end left square. The rounded end marks
   the tightest pocket. Build it as a `Box` for the square part fused with a
   `Cylinder` of radius `TEST_STRIP_WIDTH_MM / 2` centered on the first pocket
   center, or as a 2D sketch (`Rectangle` + `Circle`, or `SlotCenterPoint`-style
   outline) extruded once. Prefer the single-sketch extrude.
   - The semicircle's center is the first pocket's center, so its radius equals
     `TEST_POCKET_DIAMETER_MAX_MM / 2 + TEST_WALL_MM`: the rounded end is
     concentric with pocket 0 and keeps the overall length at
     `TEST_STRIP_LENGTH_MM`.
2. Pocket i (i = 0 … `TEST_POCKET_COUNT - 1`):
   - clearance_i = `TEST_CLEARANCE_START_MM + i * TEST_CLEARANCE_STEP_MM`
   - diameter_i = `MAGNET_DIAMETER_MM + 2 * clearance_i`
   - center x_i = `-TEST_STRIP_LENGTH_MM / 2 + TEST_WALL_MM +
     TEST_POCKET_DIAMETER_MAX_MM / 2 + i * TEST_PITCH_MM`, y = 0
   - cut `_magnet_pocket(diameter_i, x_i)`.
3. Print a table of pocket index → x position → clearance → diameter when this
   component is built, so the maker can map pockets to clearance values (pocket
   0 is at the rounded end).

### Derived quantities (compute, do not hard-code)

- `POCKET_DIAMETER_MM = MAGNET_DIAMETER_MM + 2 * MAGNET_CLEARANCE_MM`
- `POCKET_DEPTH_MM = MAGNET_HEIGHT_MM + MAGNET_DEPTH_CLEARANCE_MM`
- `BODY_THICKNESS_MM = POCKET_DEPTH_MM + POCKET_ROOF_MM`
- `TOTAL_HEIGHT_MM = BODY_THICKNESS_MM + LETTER_EMBOSS_MM`
- `TEST_CLEARANCE_MAX_MM = TEST_CLEARANCE_START_MM + (TEST_POCKET_COUNT - 1) * TEST_CLEARANCE_STEP_MM`
- `TEST_POCKET_DIAMETER_MAX_MM = MAGNET_DIAMETER_MM + 2 * TEST_CLEARANCE_MAX_MM`
- `TEST_PITCH_MM = TEST_POCKET_DIAMETER_MAX_MM + TEST_WALL_MM`
- `TEST_STRIP_WIDTH_MM = TEST_POCKET_DIAMETER_MAX_MM + 2 * TEST_WALL_MM`
- `TEST_STRIP_LENGTH_MM = TEST_POCKET_COUNT * TEST_PITCH_MM + TEST_WALL_MM`

Since CLI flags override base constants, the builders must recompute derived
values from their (keyword) arguments — e.g. `build_part(component, *,
magnet_clearance=MAGNET_CLEARANCE_MM, ...)` computes the pocket diameter inside
— rather than reading module-level derived constants that were frozen at import
time. Module-level derived constants are fine for documentation/defaults but the
CLI path must honor the flags.

## Constants to define

| Constant | Default | CLI flag | Notes |
| --- | --- | --- | --- |
| `MAGNET_DIAMETER_MM` | 6.3625 | `--magnet-diameter` | effective magnet diameter from the fit test |
| `MAGNET_HEIGHT_MM` | 6.35 | `--magnet-height` | measured magnet length (1/4") |
| `MAGNET_CLEARANCE_MM` | 0.10 | `--magnet-clearance` | per-side radial clearance, coin pocket |
| `MAGNET_DEPTH_CLEARANCE_MM` | 0.20 | `--magnet-depth-clearance` | extra pocket depth beyond magnet length |
| `POCKET_ROOF_MM` | 1.2 | — | material above pocket ceiling |
| `COIN_DIAMETER_MM` | 24.26 | `--coin-diameter` | US quarter |
| `LETTER_HEIGHT_MM` | 14.0 | `--letter-height` | glyph Y extent |
| `LETTER_EMBOSS_MM` | 1.0 | `--letter-emboss` | letter height above top face |
| `TEST_CLEARANCE_START_MM` | 0.30 | `--test-clearance-start` | tightest test pocket clearance |
| `TEST_CLEARANCE_STEP_MM` | 0.15 | `--test-clearance-step` | clearance increment |
| `TEST_POCKET_COUNT` | 6 | `--test-pocket-count` | int, no unit suffix |
| `TEST_WALL_MM` | 1.2 | — | min wall around/between test pockets |
| `POCKET_DIAMETER_MM` | 6.5625 | — | derived (see above) |
| `POCKET_DEPTH_MM` | 6.55 | — | derived |
| `BODY_THICKNESS_MM` | 7.75 | — | derived |
| `TOTAL_HEIGHT_MM` | 8.75 | — | derived |
| `TEST_CLEARANCE_MAX_MM` | 1.05 | — | derived |
| `TEST_POCKET_DIAMETER_MAX_MM` | 6.8625 | — | derived |
| `TEST_PITCH_MM` | 8.0625 | — | derived |
| `TEST_STRIP_WIDTH_MM` | 9.2625 | — | derived |
| `TEST_STRIP_LENGTH_MM` | 49.575 | — | derived |
| `_FACE_OVERLAP_MM` | 0.2 | — | Boolean overshoot/overlap |
| `COMPONENTS` | `("m", "s", "magnet-test")` | — | first is default |
| `COIN_LETTERS` | `{"m": "M", "s": "S"}` | — | component → glyph |

## CLI surface

- `--component {m,s,magnet-test}` — default `m`.
- `--all` — export every component to its own file.
- One flag per CLI row above (floats, `--test-pocket-count` int). Help text from
  the `meaning`.
- `--output PATH` — only honored when a single component is exported. Default
  filename `letter-coins-<component>.stl` (`letter-coins-m.stl`,
  `letter-coins-s.stl`, `letter-coins-magnet-test.stl`).
- `--check` — run `check_part` over all components and exit non-zero on failure.
- Validate: `magnet_clearance` and test clearances > 0 is not required (0 is
  allowed) but resulting pocket diameter must be > 0; `test_pocket_count >= 1`.
- Print the resolved parameters (including derived pocket diameter/depth, body
  thickness, total height) before building.
- Remove all `PLACEHOLDER` cube code (`CUBE_SIZE_MM`, `--size`).

## File layout

- `generate.py` — single-file CLI per the above.
- `preview.py` — renders `build_part()` (the `m` coin) by default. Extend it to
  accept `--component` / render every component (e.g. `preview.png` for `m`
  plus `preview-<component>.png` for the others, or a combined sheet) so the
  `s` coin and the test strip can be visually verified too.
- `CLAUDE.md` — fill in "Coordinate system" with the convention above and add
  any non-obvious geometry decisions (e.g. font choice/fallback, letter scaling
  method).
- `README.md` — update usage (components, `--all`, test-strip workflow: print
  strip → pick clearance → `--magnet-clearance <value> --all`).
- No extra modules.

## Verification steps

1. `.venv/bin/python generate.py` writes `letter-coins-m.stl`.
2. `--component s`, `--component magnet-test`, and `--all` write their STLs.
3. `--check` passes; bounding boxes at defaults (±0.3 mm in X/Y for the
   letter-free dims; Z exact to ±0.05):
   - `m`, `s`: X 24.26, Y 24.26, Z 8.75.
   - `magnet-test`: X 49.58, Y 9.26, Z 7.75.
   Each is a single solid. Feature check: coins have 1 pocket, strip has
   `TEST_POCKET_COUNT` (e.g. count cylindrical faces whose radius < 3 mm, or
   check volume against expectation).
4. Render `preview.py` for each component and **Read** the PNGs: letter upright
   and readable from top view (+Y up, not mirrored), centered; pocket visible
   from below/centered; strip has rounded −X end and 5 pockets increasing in
   size toward +X.
5. Also sanity-check with a `--magnet-clearance 0.2` run that the coin pocket
   diameter changes (proves the flag is live).
6. `.venv/bin/black generate.py preview.py` leaves files unchanged.
7. (Maker) slice in Bambu Studio — no supports; print strip, then coins.

Environment: if `.venv` doesn't exist, create it per README
(`uv venv .venv --python 3.12 && uv pip install -r requirements.txt -r requirements-dev.txt`).

## Boolean-robustness conventions

- Pocket cutters start at z = −`_FACE_OVERLAP_MM` so they break cleanly through
  the back face.
- The letter extrusion starts at z = `BODY_THICKNESS_MM - _FACE_OVERLAP_MM` so
  it overlaps the body instead of butting the top face.
- Strip outline: build as one sketch and extrude once; if built as Box + Cylinder
  fuse, the cylinder overlaps the box (it does, by construction) — fine.

## Known risks

- **Font availability** — `Text` uses OCCT's font manager; the default font
  may be missing or fall back silently, and glyphs can come out as multiple
  faces/wires. Mitigation: use bold style; if the default renders poorly, pick an
  installed bold sans (e.g. Helvetica/Arial on macOS, DejaVu Sans) and record the
  choice in `CLAUDE.md`. Verify in the preview that both M and S read clearly.
- **Letter scaling** — `font_size` ≠ cap height; scale by measured glyph bbox so
  the Y extent is `LETTER_HEIGHT_MM`. Confirm the glyph stays inside the disc
  (M at 14 mm tall is ≈ 15 mm wide — well within 24.26 mm).
- **Letter as multiple solids** — "S" is one contour, "M" one contour; fused to
  the body they must produce exactly one solid. `check_part` catches a failure.
- **Frozen derived constants** — CLI overrides must flow into the builders (see
  Derived quantities). Verify with step 5.
- **Bridge sag on pocket ceiling** — covered by `magnet_depth_clearance`; nothing
  to model.
