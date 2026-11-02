#!/usr/bin/env python3
"""Render a multi-view PNG preview of letter-coins.

A quick visual check of `build_part`'s geometry without opening a slicer:
tessellates the solid and renders a 2x3 contact sheet (default `preview.png`). Three
panels are shaded 3D views (isometric, front, right); two are flat,
true-orthographic, height-shaded plan views (top, and a look-through bottom
that shows blind pockets); the sixth is an XZ cross-section through y = 0. Runs headless (matplotlib Agg
backend), so it works over SSH or inside a coding agent with no display.

This is a rough geometric check, not a photoreal render: matplotlib's 3D axes
use a painter's algorithm with no depth buffer, so on concave parts a face may
occasionally poke through and triangulation diagonals streak across faces. The
flat 2D panels sidestep that — they draw the part's projected footprint with
no triangulation overlay, so feature placement and spacing are unambiguous. Use the contact sheet to confirm overall shape,
orientation (+Z up, floor on z = 0), centering, and feature placement — then
slice in Bambu Studio for the real verification.

Reuses `build_part` from generate.py. With no flags it renders the first
component (the `m` coin) to `preview.png`; `--component <name>` renders one
component to `preview-<name>.png`, and `--all` renders every component.
`build_part` must stay callable with no arguments (every parameter keeps a
default), which is also what lets the repo run out of the box.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless raster backend; MUST precede the pyplot import

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

from build123d import Box, Pos  # noqa: E402

from generate import COMPONENTS, build_part  # noqa: E402

DEFAULT_OUTPUT = "preview.png"
DEFAULT_TOLERANCE_MM = 0.2  # mesh linear deflection; smaller is finer but slower
DEFAULT_DPI = 110
_SECTION_SLAB_MM = 0.01  # thickness of the y = 0 slab used for the section

# (grid_pos, name, elevation, azimuth, flat_axis) per 3D panel in a 2x3 grid.
# The two axis-aligned views read as standard front / right elevations;
# `flat_axis` is the depth axis to hide on each (None for isometric). Grid
# positions 2 and 3 hold the flat 2D true-ortho top and bottom panels, and 6
# the flat XZ section through y = 0.
_VIEWS_3D = (
    (1, "isometric", 30, -60, None),
    (4, "front (-Y)", 0, -90, "y"),
    (5, "right (+X)", 0, 0, "x"),
)

# Light direction for the cheap diffuse shading that gives the faces depth.
_LIGHT = np.array([0.3, 0.4, 0.85])


def default_output(component: str) -> Path:
    """`preview.png` for the first component, `preview-<component>.png` else."""
    if component == COMPONENTS[0]:
        return Path(DEFAULT_OUTPUT)
    return Path(f"preview-{component}.png")


def _triangles(solid, tolerance: float) -> np.ndarray:
    """Tessellate `solid` into an (n, 3, 3) array of triangle vertices."""
    vertices, faces = solid.tessellate(tolerance)
    points = np.array([(v.X, v.Y, v.Z) for v in vertices])
    return points[np.array(faces, dtype=int)]


def _face_shading(triangles: np.ndarray) -> np.ndarray:
    """Return an (n, 4) RGBA array — one grey per face by |normal . light|."""
    normals = np.cross(
        triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]
    )
    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = normals / np.where(lengths == 0, 1.0, lengths)
    light = _LIGHT / np.linalg.norm(_LIGHT)
    brightness = 0.35 + 0.65 * np.clip(np.abs(normals @ light), 0.0, 1.0)
    return np.column_stack(
        [brightness, brightness, brightness, np.ones_like(brightness)]
    )


def _draw_flat_2d(
    ax,
    triangles: np.ndarray,
    center: np.ndarray,
    half: np.ndarray,
    from_below: bool = False,
) -> None:
    """Draw a flat true-orthographic, height-shaded plan view into a 2D axes.

    Projects every triangle straight onto the XY plane and fills it with no
    edge lines (no triangulation streaks). Triangles are painted in depth order
    as seen from the viewer and shaded by height (lighter = higher Z), so an
    embossed feature reads against the face it sits on and a blind pocket
    shows through its opening. Axes keep +X right / +Y up in both views; the
    bottom view is a look-through from -Z (not mirrored), so features line up
    with the top view.

    `half` holds per-axis half-extents; equal aspect is kept so the footprint is
    never distorted, only the X/Y window is framed to the real bounding box.
    """
    z = triangles[:, :, 2].mean(axis=1)
    order = np.argsort(-z if from_below else z)  # nearest to viewer last
    z = z[order]
    zmin, zmax = triangles[:, :, 2].min(), triangles[:, :, 2].max()
    t = (z - zmin) / max(zmax - zmin, 1e-9)
    # Top: a steep curve so a 1 mm emboss on an 8 mm part still reads clearly.
    # Bottom: linear, so a blind pocket ceiling stands out from the back face.
    grey = 0.2 + 0.75 * (t if from_below else t**6)
    colors = np.column_stack([grey * 0.9, grey * 0.9, grey, np.ones_like(grey)])
    footprint = triangles[order][:, :, :2]  # drop Z -> (n, 3, 2) XY triangles
    ax.add_collection(
        PolyCollection(
            footprint,
            facecolors=colors,
            edgecolors=colors,  # same-colour edges hide anti-aliasing seams
            linewidths=0.3,
        )
    )
    ax.set_aspect("equal")
    ax.set_xlim(center[0] - half[0], center[0] + half[0])
    ax.set_ylim(center[1] - half[1], center[1] + half[1])
    if from_below:
        ax.set_title("bottom (look-through from -Z, not mirrored)")
    else:
        ax.set_title("top (XY, flat ortho)")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.grid(True, linewidth=0.3, alpha=0.4)


def _draw_section(ax, solid, center: np.ndarray, half: np.ndarray) -> None:
    """Draw the XZ cross-section of `solid` through y = 0 as filled polygons."""
    section = solid & (
        Pos(center[0], 0, center[2]) * Box(half[0] * 4, _SECTION_SLAB_MM, half[2] * 4)
    )
    if section.solids():
        vertices, faces = section.tessellate(0.05)
        pts = np.array([(v.X, v.Z) for v in vertices])
        tris = pts[np.array(faces, dtype=int)]
        ax.add_collection(
            PolyCollection(tris, facecolors=(0.45, 0.5, 0.6, 1.0), edgecolors="none")
        )
    ax.set_aspect("equal")
    ax.set_xlim(center[0] - half[0], center[0] + half[0])
    ax.set_ylim(center[2] - max(half[2], 1.0), center[2] + max(half[2], 1.0))
    ax.set_title("section XZ at y = 0 (viewed from -Y)")
    ax.set_xlabel("X")
    ax.set_ylabel("Z")
    ax.grid(True, linewidth=0.3, alpha=0.4)


def render(
    output: Path, tolerance: float, dpi: int, component: str = COMPONENTS[0]
) -> None:
    """Render the 2x2 multi-view contact sheet of `component` to `output`."""
    solid = build_part(component)
    triangles = _triangles(solid, tolerance)
    colors = _face_shading(triangles)

    points = triangles.reshape(-1, 3)
    mins = points.min(axis=0)
    maxs = points.max(axis=0)
    center = (mins + maxs) / 2
    # Per-axis half-extents (with margin) so a thin part keeps true proportions
    # instead of rendering as a sliver inside one big cubic box. A small floor,
    # scaled to overall size, keeps a perfectly flat axis from collapsing to a
    # zero-width window.
    spans = maxs - mins
    floor = max(spans.max(), 1.0) * 0.01
    half = np.maximum(spans, floor) / 2 * 1.1

    fig = plt.figure(figsize=(15, 10))
    for pos, name, elev, azim, flat in _VIEWS_3D:
        ax = fig.add_subplot(2, 3, pos, projection="3d")
        mesh = Poly3DCollection(
            triangles,
            facecolors=colors,
            edgecolors=(0, 0, 0, 0.15),
            linewidths=0.2,
        )
        ax.add_collection3d(mesh)
        ax.set_proj_type("ortho")  # true orthographic so dimensions read true
        ax.view_init(elev=elev, azim=azim)
        ax.set_xlim(center[0] - half[0], center[0] + half[0])
        ax.set_ylim(center[1] - half[1], center[1] + half[1])
        ax.set_zlim(center[2] - half[2], center[2] + half[2])
        # Box aspect proportional to the real per-axis extents: a cube stays a
        # cube and a thin plate renders at its true (thin) aspect.
        ax.set_box_aspect(tuple(half))
        ax.set_title(name)
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.set_zlabel("Z")
        # On a flat-on elevation the depth axis collapses to a line; hide its
        # ticks and label so they do not pile up at the panel edge.
        if flat == "x":
            ax.set_xticklabels([])
            ax.set_xlabel("")
        elif flat == "y":
            ax.set_yticklabels([])
            ax.set_ylabel("")
        elif flat == "z":
            ax.set_zticklabels([])
            ax.set_zlabel("")

    # Flat 2D true-ortho plan views: top (position 2) and bottom (position 3).
    _draw_flat_2d(fig.add_subplot(2, 3, 2), triangles, center, half)
    _draw_flat_2d(fig.add_subplot(2, 3, 3), triangles, center, half, True)
    # Flat XZ section through y = 0 (position 6): shows pocket depth and roof.
    _draw_section(fig.add_subplot(2, 3, 6), solid, center, half)

    fig.suptitle(f"letter-coins preview — {component}", fontsize=14)
    fig.savefig(output, dpi=dpi)
    plt.close(fig)


def _parse_args():
    p = argparse.ArgumentParser(
        description="Render a multi-view PNG preview of letter-coins.",
    )
    p.add_argument(
        "--component",
        choices=COMPONENTS,
        default=COMPONENTS[0],
        help=f"component to render. Default: {COMPONENTS[0]}.",
    )
    p.add_argument(
        "--all",
        action="store_true",
        help="render every component, each to its default PNG path.",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            f"PNG output path (single component only). Default: {DEFAULT_OUTPUT} "
            "for the first component, preview-<component>.png for the others."
        ),
    )
    p.add_argument(
        "--tolerance",
        type=float,
        default=DEFAULT_TOLERANCE_MM,
        metavar="MM",
        help=(
            "Mesh linear deflection in mm; smaller is finer but slower. "
            f"Default: {DEFAULT_TOLERANCE_MM}."
        ),
    )
    p.add_argument(
        "--dpi",
        type=int,
        default=DEFAULT_DPI,
        metavar="DPI",
        help=f"Output resolution in dots per inch. Default: {DEFAULT_DPI}.",
    )
    return p.parse_args()


def main():
    args = _parse_args()
    components = COMPONENTS if args.all else (args.component,)
    for component in components:
        output = args.output
        if output is None or args.all:
            output = default_output(component)
        render(output, args.tolerance, args.dpi, component)
        print(f"Wrote preview: {output}")


if __name__ == "__main__":
    main()
