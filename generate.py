#!/usr/bin/env python3
"""Generate STLs for letter-coins.

Quarter-sized magnetic "claim" tokens (an "M" coin and an "S" coin) plus a
magnet test strip of graded press-fit pockets. See DESIGN_BRIEF.md.

Coordinate system: right-handed; origin at the center of the footprint, back
face on the build plate at z = 0.

- +X -- coin: rightward as the letter is read from above. Test strip: along the
  bar, from the tightest pocket (-X, rounded end) to the loosest (+X, square
  end).
- +Y -- coin: "up" for the letter as read from above. Test strip: across the
  bar's width.
- +Z -- up from the back face (magnet pocket opening; sits on the build plate
  and against the whiteboard) toward the top face / top of the letter.

All components are centered in X and Y; floor on z = 0. Modelled in printed
orientation -- no rotation before export.

All geometry constants are at the top of this file; a subset is exposed on the
CLI. See --help.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from OCP.BRepAdaptor import BRepAdaptor_Surface
from build123d import (
    Align,
    Circle,
    Cylinder,
    FontStyle,
    GeomType,
    Pos,
    Rectangle,
    Text,
    export_stl,
    extrude,
)

# === Part geometry ==========================================================
# Base parameters (CLI-overridable where noted in DESIGN_BRIEF.md).
MAGNET_DIAMETER_MM = (
    6.3625  # effective magnet dia, fit-tested (nominal 3/16" was far too small)
)
MAGNET_HEIGHT_MM = 6.35  # measured magnet length along its axis (1/4")
MAGNET_CLEARANCE_MM = 0.10  # per-side radial clearance, coin pocket
MAGNET_DEPTH_CLEARANCE_MM = 0.20  # extra pocket depth beyond magnet length
POCKET_ROOF_MM = 1.2  # material between pocket ceiling and top face
COIN_DIAMETER_MM = 24.26  # US quarter
LETTER_HEIGHT_MM = 14.0  # glyph Y extent
LETTER_EMBOSS_MM = 1.0  # letter height above the coin top face
TEST_CLEARANCE_START_MM = 0.30  # per-side clearance of the tightest test pocket
TEST_CLEARANCE_STEP_MM = 0.15  # clearance increment between test pockets
TEST_POCKET_COUNT = 6  # number of pockets on the test strip
TEST_WALL_MM = 1.2  # minimum wall around/between test-strip pockets

# Font for the embossed letter: a bold sans-serif installed on macOS. OCCT
# falls back silently to its default font if this one is missing.
LETTER_FONT = "Arial"
LETTER_FONT_STYLE = FontStyle.BOLD

# Boolean overshoot so cuts/fuses never resolve a coincident face.
_FACE_OVERLAP_MM = 0.2

# Derived quantities (module-level values document the defaults; the builders
# recompute them from their keyword arguments so CLI flags stay live).
POCKET_DIAMETER_MM = MAGNET_DIAMETER_MM + 2 * MAGNET_CLEARANCE_MM
POCKET_DEPTH_MM = MAGNET_HEIGHT_MM + MAGNET_DEPTH_CLEARANCE_MM
BODY_THICKNESS_MM = POCKET_DEPTH_MM + POCKET_ROOF_MM
TOTAL_HEIGHT_MM = BODY_THICKNESS_MM + LETTER_EMBOSS_MM
TEST_CLEARANCE_MAX_MM = (
    TEST_CLEARANCE_START_MM + (TEST_POCKET_COUNT - 1) * TEST_CLEARANCE_STEP_MM
)
TEST_POCKET_DIAMETER_MAX_MM = MAGNET_DIAMETER_MM + 2 * TEST_CLEARANCE_MAX_MM
TEST_PITCH_MM = TEST_POCKET_DIAMETER_MAX_MM + TEST_WALL_MM
TEST_STRIP_WIDTH_MM = TEST_POCKET_DIAMETER_MAX_MM + 2 * TEST_WALL_MM
TEST_STRIP_LENGTH_MM = TEST_POCKET_COUNT * TEST_PITCH_MM + TEST_WALL_MM

PROJECT = "letter-coins"
COMPONENTS = ("m", "s", "magnet-test")
COIN_LETTERS = {"m": "M", "s": "S"}


def default_output(component: str) -> str:
    return f"{PROJECT}-{component}.stl"


# ----------------------------------------------------------------------------
# Derived-parameter helpers
# ----------------------------------------------------------------------------


def _derived(
    *,
    magnet_diameter: float = MAGNET_DIAMETER_MM,
    magnet_height: float = MAGNET_HEIGHT_MM,
    magnet_clearance: float = MAGNET_CLEARANCE_MM,
    magnet_depth_clearance: float = MAGNET_DEPTH_CLEARANCE_MM,
    letter_emboss: float = LETTER_EMBOSS_MM,
    test_clearance_start: float = TEST_CLEARANCE_START_MM,
    test_clearance_step: float = TEST_CLEARANCE_STEP_MM,
    test_pocket_count: int = TEST_POCKET_COUNT,
    **_ignored,
) -> dict:
    """Recompute every derived dimension from the (possibly overridden) inputs."""
    pocket_depth = magnet_height + magnet_depth_clearance
    body_thickness = pocket_depth + POCKET_ROOF_MM
    test_clearance_max = (
        test_clearance_start + (test_pocket_count - 1) * test_clearance_step
    )
    test_pocket_diameter_max = magnet_diameter + 2 * test_clearance_max
    test_pitch = test_pocket_diameter_max + TEST_WALL_MM
    return {
        "pocket_diameter": magnet_diameter + 2 * magnet_clearance,
        "pocket_depth": pocket_depth,
        "body_thickness": body_thickness,
        "total_height": body_thickness + letter_emboss,
        "test_clearance_max": test_clearance_max,
        "test_pocket_diameter_max": test_pocket_diameter_max,
        "test_pitch": test_pitch,
        "test_strip_width": test_pocket_diameter_max + 2 * TEST_WALL_MM,
        "test_strip_length": test_pocket_count * test_pitch + TEST_WALL_MM,
    }


def test_pockets(
    *,
    magnet_diameter: float = MAGNET_DIAMETER_MM,
    test_clearance_start: float = TEST_CLEARANCE_START_MM,
    test_clearance_step: float = TEST_CLEARANCE_STEP_MM,
    test_pocket_count: int = TEST_POCKET_COUNT,
    **kwargs,
) -> list[tuple[int, float, float, float]]:
    """Return (index, x, clearance, diameter) for each test-strip pocket."""
    d = _derived(
        magnet_diameter=magnet_diameter,
        test_clearance_start=test_clearance_start,
        test_clearance_step=test_clearance_step,
        test_pocket_count=test_pocket_count,
        **kwargs,
    )
    x0 = -d["test_strip_length"] / 2 + TEST_WALL_MM + d["test_pocket_diameter_max"] / 2
    pockets = []
    for i in range(test_pocket_count):
        clearance = test_clearance_start + i * test_clearance_step
        diameter = magnet_diameter + 2 * clearance
        pockets.append((i, x0 + i * d["test_pitch"], clearance, diameter))
    return pockets


# ----------------------------------------------------------------------------
# Geometry helpers
# ----------------------------------------------------------------------------


def _magnet_pocket(diameter: float, depth: float, x: float = 0.0):
    """Blind pocket cutter: z = -overlap .. depth, centered at (x, 0)."""
    height = depth + _FACE_OVERLAP_MM
    return Pos(x, 0, -_FACE_OVERLAP_MM) * Cylinder(
        radius=diameter / 2,
        height=height,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )


def _letter_sketch(letter: str, letter_height: float):
    """Glyph sketch scaled so its Y extent is `letter_height`, bbox-centered.

    `font_size` is not cap height, so build once at a probe size, measure the
    glyph's bounding box and rescale linearly (outlines scale with font size).
    """

    def make(size):
        return Text(
            letter,
            font_size=size,
            font=LETTER_FONT,
            font_style=LETTER_FONT_STYLE,
            align=(Align.CENTER, Align.CENTER),
        )

    probe = make(letter_height)
    probe_h = probe.bounding_box().size.Y
    glyph = make(letter_height * letter_height / probe_h)
    c = glyph.bounding_box().center()
    return Pos(-c.X, -c.Y, 0) * glyph


def _build_coin(
    letter: str,
    *,
    coin_diameter: float = COIN_DIAMETER_MM,
    letter_height: float = LETTER_HEIGHT_MM,
    letter_emboss: float = LETTER_EMBOSS_MM,
    **kwargs,
):
    d = _derived(letter_emboss=letter_emboss, **kwargs)
    body = Cylinder(
        radius=coin_diameter / 2,
        height=d["body_thickness"],
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    body -= _magnet_pocket(d["pocket_diameter"], d["pocket_depth"])
    glyph = extrude(
        _letter_sketch(letter, letter_height),
        amount=letter_emboss + _FACE_OVERLAP_MM,
    )
    glyph = Pos(0, 0, d["body_thickness"] - _FACE_OVERLAP_MM) * glyph
    return body + glyph


def _build_magnet_test(**kwargs):
    d = _derived(**kwargs)
    pockets = test_pockets(**kwargs)
    width = d["test_strip_width"]
    length = d["test_strip_length"]
    x_round = pockets[0][1]  # rounded end is concentric with pocket 0
    # Square part runs from the first pocket center to the +X end; the circle
    # supplies the rounded -X end. One sketch, extruded once.
    rect_len = length / 2 - x_round
    outline = Pos(x_round + rect_len / 2, 0) * Rectangle(rect_len, width)
    outline += Pos(x_round, 0) * Circle(width / 2)
    strip = extrude(outline, amount=d["body_thickness"])
    for _, x, _, diameter in pockets:
        strip -= _magnet_pocket(diameter, d["pocket_depth"], x)
    return strip


# ----------------------------------------------------------------------------
# Assembly
# ----------------------------------------------------------------------------


def build_part(component: str = COMPONENTS[0], **params):
    """Build one component; with no arguments returns the first (`m`) coin.

    `params` accepts the CLI-exposed parameters by their DESIGN_BRIEF names
    (magnet_diameter, magnet_clearance, coin_diameter, letter_height, ...).
    """
    if component in COIN_LETTERS:
        return _build_coin(COIN_LETTERS[component], **params)
    if component == "magnet-test":
        return _build_magnet_test(**params)
    raise ValueError(f"unknown component {component!r}; choose from {COMPONENTS}")


# ----------------------------------------------------------------------------
# Geometry self-check
# ----------------------------------------------------------------------------


def _count_pockets(solid, max_radius: float) -> int:
    """Count distinct cylinder axes with radius <= `max_radius` (pockets).

    The coin rim and the strip's rounded end are larger than any pocket (by at
    least a wall), so only pocket walls qualify.
    """
    centers = set()
    for f in solid.faces():
        if f.geom_type != GeomType.CYLINDER:
            continue
        cyl = BRepAdaptor_Surface(f.wrapped).Cylinder()
        if cyl.Radius() > max_radius + 1e-3:
            continue
        loc = cyl.Location()
        centers.add((round(loc.X(), 2), round(loc.Y(), 2)))
    return len(centers)


def _expected(component: str, **params) -> tuple[tuple[float, float, float], int]:
    d = _derived(**params)
    if component in COIN_LETTERS:
        dia = params.get("coin_diameter", COIN_DIAMETER_MM)
        return (dia, dia, d["total_height"]), 1
    count = params.get("test_pocket_count", TEST_POCKET_COUNT)
    return (d["test_strip_length"], d["test_strip_width"], d["body_thickness"]), count


def check_part(components=COMPONENTS, **params) -> bool:
    """Build each component and assert bbox, single solid and pocket count."""
    xy_tol, z_tol = 0.3, 0.05
    ok = True
    print("geometry self-check:")
    for comp in components:
        solid = build_part(comp, **params)
        bbox = solid.bounding_box()
        size = bbox.size
        n_solids = len(solid.solids())
        d = _derived(**params)
        max_pocket = max(d["pocket_diameter"], d["test_pocket_diameter_max"])
        n_pockets = _count_pockets(solid, max_pocket / 2)
        (ex, ey, ez), want_pockets = _expected(comp, **params)
        print(f"  [{comp}]")
        print(f"    solids       : {n_solids}")
        print(f"    pockets      : {n_pockets} (expected {want_pockets})")
        print(f"    bounding box : {size.X:.2f} x {size.Y:.2f} x {size.Z:.2f} mm")
        print(
            f"    min .. max   : "
            f"({bbox.min.X:.2f}, {bbox.min.Y:.2f}, {bbox.min.Z:.2f}) .. "
            f"({bbox.max.X:.2f}, {bbox.max.Y:.2f}, {bbox.max.Z:.2f})"
        )
        problems = []
        if n_solids != 1:
            problems.append(f"expected a single watertight solid, got {n_solids}")
        elif not solid.solids()[0].is_valid():
            problems.append("solid is not valid")
        for axis, got, want, tol in (
            ("X", size.X, ex, xy_tol),
            ("Y", size.Y, ey, xy_tol),
            ("Z", size.Z, ez, z_tol),
        ):
            if abs(got - want) > tol:
                problems.append(f"{axis} = {got:.3f} mm, expected {want:.3f} +/- {tol}")
        if abs(bbox.min.Z) > 1e-6:
            problems.append(f"floor at z = {bbox.min.Z:.3f}, expected 0")
        for axis, lo, hi in (
            ("X", bbox.min.X, bbox.max.X),
            ("Y", bbox.min.Y, bbox.max.Y),
        ):
            if abs(lo + hi) / 2 > 0.3:
                problems.append(f"not centered in {axis} (center {(lo + hi) / 2:.3f})")
        if n_pockets != want_pockets:
            problems.append(f"expected {want_pockets} pockets, found {n_pockets}")
        for p in problems:
            print(f"    FAIL: {p}")
        if problems:
            ok = False
        else:
            print("    OK")
    return ok


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

# (flag, dest, type, default, help)
_CLI_PARAMS = (
    (
        "--magnet-diameter",
        "magnet_diameter",
        float,
        MAGNET_DIAMETER_MM,
        'measured magnet cylinder diameter in mm (3/16")',
    ),
    (
        "--magnet-height",
        "magnet_height",
        float,
        MAGNET_HEIGHT_MM,
        'measured magnet cylinder length along its axis in mm (1/4")',
    ),
    (
        "--magnet-clearance",
        "magnet_clearance",
        float,
        MAGNET_CLEARANCE_MM,
        "per-side radial clearance of the coin's magnet pocket in mm (press fit)",
    ),
    (
        "--magnet-depth-clearance",
        "magnet_depth_clearance",
        float,
        MAGNET_DEPTH_CLEARANCE_MM,
        "extra pocket depth beyond the magnet length in mm",
    ),
    (
        "--coin-diameter",
        "coin_diameter",
        float,
        COIN_DIAMETER_MM,
        "coin outer diameter in mm (US quarter)",
    ),
    (
        "--letter-height",
        "letter_height",
        float,
        LETTER_HEIGHT_MM,
        "height (Y extent) of the embossed glyph in mm",
    ),
    (
        "--letter-emboss",
        "letter_emboss",
        float,
        LETTER_EMBOSS_MM,
        "how far the letter stands proud of the coin top face in mm",
    ),
    (
        "--test-clearance-start",
        "test_clearance_start",
        float,
        TEST_CLEARANCE_START_MM,
        "per-side clearance of the tightest test-strip pocket in mm",
    ),
    (
        "--test-clearance-step",
        "test_clearance_step",
        float,
        TEST_CLEARANCE_STEP_MM,
        "clearance increment between adjacent test-strip pockets in mm",
    ),
    (
        "--test-pocket-count",
        "test_pocket_count",
        int,
        TEST_POCKET_COUNT,
        "number of pockets on the test strip",
    ),
)


def _parse_args():
    p = argparse.ArgumentParser(description="Generate STLs for letter-coins.")
    p.add_argument(
        "--component",
        choices=COMPONENTS,
        default=COMPONENTS[0],
        help=f"component to export. Default: {COMPONENTS[0]}.",
    )
    p.add_argument(
        "--all",
        action="store_true",
        help="export every component, each to its own letter-coins-<component>.stl.",
    )
    for flag, dest, typ, default, help_text in _CLI_PARAMS:
        p.add_argument(
            flag,
            dest=dest,
            type=typ,
            default=default,
            help=f"{help_text}. Default: {default}.",
        )
    p.add_argument(
        "--output",
        type=Path,
        default=None,
        metavar="PATH",
        help="STL output path (single component only). "
        "Default: letter-coins-<component>.stl.",
    )
    p.add_argument(
        "--check",
        action="store_true",
        help="run the geometry self-check over all components and exit.",
    )
    args = p.parse_args()

    params = {dest: getattr(args, dest) for _, dest, *_ in _CLI_PARAMS}
    d = _derived(**params)
    if d["pocket_diameter"] <= 0:
        p.error("magnet pocket diameter must be > 0")
    if params["test_pocket_count"] < 1:
        p.error("--test-pocket-count must be >= 1")
    if any(dia <= 0 for *_, dia in test_pockets(**params)):
        p.error("every test-strip pocket diameter must be > 0")
    if args.all and args.output is not None:
        p.error("--output applies only when a single component is exported")
    return args, params


def _print_pocket_table(params) -> None:
    print("magnet-test pockets (pocket 0 is at the rounded -X end):")
    print("  index      x (mm)   clearance (mm)   diameter (mm)")
    for i, x, clearance, diameter in test_pockets(**params):
        print(f"  {i:5d}  {x:10.3f}  {clearance:15.3f}  {diameter:14.4f}")


def main():
    args, params = _parse_args()

    if args.check:
        sys.exit(0 if check_part(**params) else 1)

    components = COMPONENTS if args.all else (args.component,)
    d = _derived(**params)

    print("letter-coins -- resolved parameters:")
    for key, value in params.items():
        print(f"  {key:24s}: {value}")
    for key in ("pocket_diameter", "pocket_depth", "body_thickness", "total_height"):
        print(f"  {key:24s}: {d[key]:.4f} (derived)")
    print(f"  {'font':24s}: {LETTER_FONT} ({LETTER_FONT_STYLE.name.lower()})")
    print()

    for comp in components:
        if comp == "magnet-test":
            _print_pocket_table(params)
        solid = build_part(comp, **params)
        out_path = (
            args.output if args.output is not None else Path(default_output(comp))
        )
        if str(out_path.parent) not in ("", "."):
            out_path.parent.mkdir(parents=True, exist_ok=True)
        export_stl(solid, str(out_path))
        print(f"Wrote STL: {out_path}")


if __name__ == "__main__":
    main()
