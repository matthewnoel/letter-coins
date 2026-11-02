# Design Brief — letter-coins

Quarter-sized magnetic "claim" tokens for a magnetic whiteboard: a thick disc
with a single embossed letter on top and a blind pocket in the back that takes a
small press-fit cylindrical magnet. Two coin variants — **M** (Matthew) and
**S** (Samantha) — plus a low-filament **magnet test strip** of graded pockets
used to dial in the magnet press fit before printing the coins. Each component
is a single printed piece in a single filament. At default parameters a coin is
≈ 24.26 mm diameter × 8.75 mm tall; the test strip is ≈ 49.6 × 9.3 × 7.75 mm.

- **Project name:** `letter-coins`
- **Units:** mm (the magnet was measured in inches: 3/16" dia × 1/4" long,
  converted to 4.7625 mm × 6.35 mm).
- **Components:** `m`, `s`, `magnet-test` — `m` is the default (first).

## Coordinate system

Right-handed. Origin at the center of the part's footprint on the build plate.

- **+X** — for a coin, rightward as the letter is read from above. For the test
  strip, along the bar's length, from the tightest pocket (−X, rounded end)
  toward the loosest pocket (+X, square end).
- **+Y** — for a coin, "up" for the letter as read from above (the letter's
  baseline-to-cap direction). For the test strip, across the bar's width.
- **+Z** — up from the back face toward the top of the embossed letter. The back
  face (where the magnet pocket opens, and which sits against the whiteboard in
  use) is on the build plate at z = 0.

Every component is centered in X and Y.

## Parameters

Derived parameters carry their formula in `meaning` and **must be implemented as
live Python**, never as the pre-computed number — otherwise tuning
`--magnet-clearance` etc. would silently stop changing the printed part.

| name | default | units | CLI | meaning |
|------|---------|-------|-----|---------|
| `magnet_diameter` | 6.3625 | mm | yes | effective magnet diameter from the fit test (nominal 3/16" = 4.7625 was far too small) |
| `magnet_height` | 6.35 | mm | yes | measured magnet cylinder length along its axis (1/4") |
| `magnet_clearance` | 0.10 | mm | yes | per-side radial clearance of the coin's magnet pocket (press fit) |
| `magnet_depth_clearance` | 0.20 | mm | yes | extra pocket depth beyond the magnet length |
| `pocket_roof` | 1.2 | mm | no | solid material between pocket ceiling and the coin/strip top face |
| `coin_diameter` | 24.26 | mm | yes | coin outer diameter (US quarter) |
| `letter_height` | 14.0 | mm | yes | height (Y extent) of the embossed glyph |
| `letter_emboss` | 1.0 | mm | yes | how far the letter stands proud of the coin top face |
| `pocket_diameter` | 6.5625 | mm | no | derived: `magnet_diameter + 2 * magnet_clearance` |
| `pocket_depth` | 6.55 | mm | no | derived: `magnet_height + magnet_depth_clearance` |
| `body_thickness` | 7.75 | mm | no | derived: `pocket_depth + pocket_roof` |
| `total_height` | 8.75 | mm | no | derived: `body_thickness + letter_emboss` |
| `test_clearance_start` | 0.30 | mm | yes | per-side clearance of the tightest test-strip pocket |
| `test_clearance_step` | 0.15 | mm | yes | clearance increment between adjacent test-strip pockets |
| `test_pocket_count` | 6 | count | yes | number of pockets on the test strip |
| `test_wall` | 1.2 | mm | no | minimum wall around/between test-strip pockets |
| `test_clearance_max` | 1.05 | mm | no | derived: `test_clearance_start + (test_pocket_count - 1) * test_clearance_step` |
| `test_pocket_diameter_max` | 6.8625 | mm | no | derived: `magnet_diameter + 2 * test_clearance_max` |
| `test_pitch` | 8.0625 | mm | no | derived: `test_pocket_diameter_max + test_wall` (center-to-center pocket spacing) |
| `test_strip_width` | 9.2625 | mm | no | derived: `test_pocket_diameter_max + 2 * test_wall` (Y extent) |
| `test_strip_length` | 49.575 | mm | no | derived: `test_pocket_count * test_pitch + test_wall` (X extent) |

The test strip's height is `body_thickness` (same pocket depth and roof as the
coins) — not a separate parameter.

## 1. Context & assembly

Matthew and Samantha use these on a magnetic whiteboard at home to "claim"
items: stick your coin next to an item. The **M** coin is Matthew's, the **S**
coin Samantha's. They are finished functional parts, printed one model per
letter (the maker duplicates copies in Bambu Studio as needed).

Each coin mates with one purchased cylindrical neodymium magnet (≈ 4.76 mm
diameter × 6.35 mm long — taller than wide, like a tiny soda can). The magnet is
pressed, axis vertical, into a blind pocket that opens on the coin's back face;
it is retained by friction alone (no glue). In use the back face sits flat
against the whiteboard with the magnet's end face toward the board.

Controlling relationships:

- `pocket_diameter = magnet_diameter + 2 * magnet_clearance`
- `pocket_depth = magnet_height + magnet_depth_clearance` — the magnet ends up
  flush to at most `magnet_depth_clearance` below the back face, never proud of
  it, so the coin never rocks on the board.
- `body_thickness = pocket_depth + pocket_roof`

Because the magnet is 6.35 mm long, the coin is deliberately thick (poker-chip /
game-token proportions, ≈ 8.75 mm), not a real-coin 1.75 mm. This was an
explicit choice (option "A" in the interview) for the strongest hold: the
magnet's pole face sits right at the board.

The **magnet test strip** exists to find the right `magnet_clearance` with
minimal filament: a bar of `test_pocket_count` pockets, each of identical depth
and roof to the coin pocket, with per-side clearances stepping from
`test_clearance_start` by `test_clearance_step`. The maker presses a magnet into
each, picks the tightest pocket that still lets the magnet seat fully and hold,
and passes that value as `--magnet-clearance` when exporting the coins.

## 2. Tolerances & fits

- **Magnet ↔ coin pocket:** press / friction fit. Default
  `magnet_clearance = 0.10 mm` per side (≈ snug press on a calibrated FDM
  printer). CLI flag, because the right value is printer- and filament-dependent
  and is the whole point of the test strip.
- **Pocket depth:** `magnet_depth_clearance = 0.20 mm` extra depth, CLI. It
  absorbs bridge sag on the pocket ceiling so the magnet still seats flush or
  slightly recessed. If hold strength is weak, it can be reduced.
- **Test strip:** clearances 0.30, 0.45, 0.60, 0.75, 0.90, 1.05 mm per side by
  default (widened after the first strip at 0.05–0.25 mm was far too tight —
  no pocket accepted the magnet; 0.15 mm steps so pockets differ visibly) (start/step/count all CLI).
- **Thin features:** `pocket_roof = 1.2 mm` (6 layers at 0.2 mm) and
  `test_wall = 1.2 mm` (3 perimeters with a 0.4 mm nozzle) are the thinnest
  features; don't go below them. The coin's wall around its pocket is ≈ 9.6 mm —
  no concern.

## 3. Print constraints

- **Orientation:** every component prints back face down (z = 0 on the plate),
  pocket opening on the plate, letter (coin) / top face (strip) up. Modelled in
  this orientation, so the STL is print-ready.
- **Overhangs / bridging:** the only unsupported span is each pocket's flat
  ceiling, a ≈ 5 mm circular bridge — trivially bridgeable. The embossed letter
  is a straight vertical extrusion on top; no overhangs. **Support-free.**
- **Adhesion:** coin footprint is a 24 mm disc with a 5 mm hole — fine without
  brim in PLA. The test strip is small (≈ 33 × 7.7 mm) and 7.75 mm tall; PLA
  should hold without brim, but a brim is an acceptable slicer choice if it
  lifts.
- **Edges:** plain vertical coin edge — no chamfer or fillet (maker's choice).
- **Boolean notes:** (a) each pocket cutter breaks through the bottom face at
  z = 0 — extend it below z = 0 by an overshoot; (b) the letter is fused onto the
  top face at z = `body_thickness` — sink its base below the top face by an
  overlap so the fuse does not resolve a coincident face.

## 4. Named size presets

- Coin diameter defaults to a **US quarter: 24.26 mm**. That is the only preset;
  otherwise fully parametric. No lookup module needed.
- Magnet: the maker's measured magnet (3/16" × 1/4"), entered as the default
  `magnet_diameter` / `magnet_height`.

## 5. Verification approach

Expected bounding boxes at default parameters:

- `m`, `s`: X ≈ 24.26, Y ≈ 24.26, Z = 8.75 mm (letter extents in X/Y are well
  inside the disc).
- `magnet-test`: X ≈ 49.58, Y ≈ 9.26, Z = 7.75 mm.

Checks: each component is a single watertight solid; coins have exactly one
pocket, the strip has `test_pocket_count`; `preview.py` render shows the letter
upright and readable from +Z (+Y up), pocket centered underneath. Slice in Bambu
Studio — confirm no supports needed. Physical: print the test strip, press a
magnet into each pocket, pick the clearance; then print a coin and confirm the
magnet seats and the coin holds on the whiteboard.

## 6. Reference sketches

None — `reference/` contains only its README. The sketch that would help most is
a section through the coin showing pocket, roof, and letter; the dimensions in
this brief fully define it.

## 7. Out of scope / non-goals

- No multi-color / filament-swap features — single filament per coin.
- No raised rim, no edge chamfer/fillet/knurl.
- No letters other than M and S as components (no arbitrary-text flag needed),
  no letter on the back.
- No glue channels, no snap-in magnet retention, no mid-print-pause magnet
  embedding.
- No multi-coin print plate — one model per STL.
- No labels/numbers on the test strip; the rounded end is the only marker.

## 8. Open questions

1. **Font** — any easy, readable bold sans-serif. Leaning: the build123d/OCCT
   default font, bold style. Resolved by the build agent picking whatever bold
   sans is available and confirming in the preview that M and S are readable.
2. **Hold strength with the 0.2 mm recess** — leaning: fine. Resolved by the
   first printed coin on the board; if weak, lower `--magnet-depth-clearance`.
3. **Final `magnet_clearance`** — resolved by the test strip print; default
   0.10 mm stands until then.
