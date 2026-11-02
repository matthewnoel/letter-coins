# letter-coins

Quarter-sized magnetic "claim" tokens for a magnetic whiteboard: a thick disc
with an embossed **M** or **S** on top and a blind pocket in the back for a
3/16" × 1/4" press-fit cylindrical magnet — plus a small test strip of graded
pockets for dialling in the press fit first. A single-file `build123d` CLI
that generates printable STLs. Scaffolded by Partwright.

| Component | What it is | Default size (mm) |
| --- | --- | --- |
| `m` (default) | coin with an embossed "M" | 24.26 dia × 8.75 |
| `s` | coin with an embossed "S" | 24.26 dia × 8.75 |
| `magnet-test` | bar of 6 magnet pockets, clearance 0.30–1.05 mm | 49.58 × 9.26 × 7.75 |

Every STL is print-ready as exported: back face (pocket opening) down on the
plate, no supports.

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

`--output PATH` overrides the filename when a single component is exported.
Run the geometry self-check (bounding box, single solid, pocket count for each
component):

```sh
.venv/bin/python generate.py --check
```

See all options (magnet size, clearances, coin diameter, letter height/emboss,
test-strip start/step/count):

```sh
.venv/bin/python generate.py --help
```

### Dialling in the magnet fit (test strip workflow)

1. Print the strip: `.venv/bin/python generate.py --component magnet-test`.
   The build prints a table mapping each pocket to its clearance. Pocket 0 is
   at the **rounded end** (tightest); clearance grows by 0.15 mm per pocket
   toward the square end:

   | pocket | per-side clearance (mm) | pocket diameter (mm) |
   | --- | --- | --- |
   | 0 (rounded end) | 0.30 | 5.3625 |
   | 1 | 0.45 | 5.6625 |
   | 2 | 0.60 | 5.9625 |
   | 3 | 0.75 | 6.2625 |
   | 4 | 0.90 | 6.5625 |
   | 5 (square end) | 1.05 | 6.8625 |

2. Press a magnet into each pocket. Pick the tightest pocket where the magnet
   seats fully and holds firmly.
3. Export the coins with that clearance, e.g.:

   ```sh
   .venv/bin/python generate.py --magnet-clearance 0.15 --all
   ```

   (This also re-exports the strip; just print the coins.) Shift the strip's
   range with `--test-clearance-start`, `--test-clearance-step` and
   `--test-pocket-count` if none of the pockets fit well.

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
