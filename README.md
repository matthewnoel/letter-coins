# letter-coins

Quarter-sized magnetic "claim" tokens for a magnetic whiteboard: a thick disc
with an embossed **M** or **S** on top and a blind pocket in the back for a
press-fit cylindrical magnet (sold as 3/16" × 1/4") — plus a small test strip of graded
pockets for dialling in the press fit first. A single-file `build123d` CLI
that generates printable STLs. Scaffolded by Partwright.

| Component | What it is | Default size (mm) |
| --- | --- | --- |
| `m` (default) | coin with an embossed "M" | 24.26 dia × 8.75 |
| `s` | coin with an embossed "S" | 24.26 dia × 8.75 |
| `magnet-test` | bar of 6 magnet pockets, clearance 0.30–1.05 mm | 59.18 × 10.86 × 7.75 |

Every STL is print-ready as exported: back face (pocket opening) down on the
plate, no supports.

### Magnet fit (as printed)

The magnets are nominally 3/16" (4.76 mm) diameter × 1/4" (6.35 mm) long, but
pockets sized from 4.76 mm were far too tight. A test strip showed a 6.5625 mm
pocket gives a good press fit, so the default `--magnet-diameter` is the
**effective** diameter 6.3625 mm, with the normal 0.10 mm per-side
`--magnet-clearance` on top: pocket = 6.3625 + 2 × 0.10 = 6.5625 mm, 6.55 mm
deep. The coins exported with the defaults are the ones that were printed and
confirmed to work.

## Prerequisites

- [uv](https://docs.astral.sh/uv/)

## Environment Setup

```sh
uv venv .venv --python 3.12
uv pip install -r requirements.txt
# dev tools (black); needed to run the format step in CLAUDE.md
uv pip install -r requirements-dev.txt
```

## Usage

Export the default component (the `m` coin) to `letter-coins-m.stl`:

```sh
.venv/bin/python generate.py
```

Pick a component, or export all three at once (`letter-coins-m.stl`,
`letter-coins-s.stl`, `letter-coins-magnet-test.stl`):

```sh
.venv/bin/python generate.py --component s
.venv/bin/python generate.py --component magnet-test
.venv/bin/python generate.py --all
```

Make a coin for **any single character** (as Arial Bold renders it) with
`--letter`; the file is named from the character (`letter-coins-commercial-at.stl`
here; `M` → `letter-coins-m.stl`, lowercase `m` → `letter-coins-lower-m.stl`):

```sh
.venv/bin/python generate.py --letter '@'
.venv/bin/python preview.py --letter '@'   # -> preview-commercial-at.png
```

Wide or flat glyphs (`W`, `w`, `-`, `_`, ...) are shrunk automatically so they
keep a 1.5 mm margin from the coin edge; the build prints a note when that
happens. Characters the font has no glyph for are rejected.

`--output PATH` overrides the filename when a single component is exported.
Run the geometry self-check (bounding box, single solid, pocket count for each
component; add `--letter CHAR` to check that coin too):

```sh
.venv/bin/python generate.py --check
```

See all options (magnet size, clearances, coin diameter, letter height/emboss,
test-strip start/step/count):

```sh
.venv/bin/python generate.py --help
```

### Dialling in the magnet fit (test strip workflow)

Only needed for new magnets or a different printer/filament. Note that the
strip's pockets are sized from `--magnet-diameter`, and the default clearance
range (0.30–1.05 mm per side, in 0.15 mm steps) is still the wide range used to
find the fit — with the corrected magnet diameter it is far too loose. Re-centre
it around a normal press fit when re-testing:

1. Print the strip, giving your best magnet diameter and a tight range, e.g.:

   ```sh
   .venv/bin/python generate.py --component magnet-test \
       --magnet-diameter 6.3625 --test-clearance-start 0.00 --test-clearance-step 0.10
   ```

   The build prints a table mapping each pocket to its clearance and diameter.
   Pocket 0 is at the **rounded end** (tightest); pockets grow toward the
   square end.
2. Press a magnet into each pocket. Pick the tightest pocket where the magnet
   seats fully and holds firmly. If none are close, widen the step rather than
   guessing — but once you find the fit, fold a large miss into
   `--magnet-diameter`, not into the clearance.
3. Export the coins so that `magnet_diameter + 2 × magnet_clearance` equals the
   winning pocket's diameter, e.g. with the 0.10 mm default clearance:

   ```sh
   .venv/bin/python generate.py --magnet-diameter <pocket diameter - 0.2> --all
   ```

   (This also re-exports the strip; just print the coins.)

## Visual preview

Render a multi-view PNG of the current geometry without opening a slicer:

```sh
.venv/bin/python preview.py            # m coin -> preview.png
.venv/bin/python preview.py --component magnet-test
.venv/bin/python preview.py --all      # preview.png, preview-s.png, preview-magnet-test.png
```

Each is a 2×3 contact sheet: isometric, top, bottom (look-through, shows the
blind pockets), front, right, and an XZ section through y = 0.
Tune mesh fineness with `--tolerance` (smaller = finer) and resolution with
`--dpi`. The renderer ships in `requirements.txt`, so it works after the standard
setup above.

## Working with Claude

Open this folder in Claude Code. `CLAUDE.md` tells the agent to edit
`build_part`, regenerate the STLs, render the previews, and visually verify
them before declaring a change done. Put reference drawings — SVGs from
`partwright sketch`, photos — in `reference/` so the agent can see your design
intent.

## Development

Format the code (requires the dev deps from the setup step above):

```sh
.venv/bin/black *.py
```
