# Reference drawings

Design-intent references for letter-coins live here. They tell a build agent
(and future you) what the part should look like *before* any geometry is
written — drop things in before you start, and point the build agent at them.

- **SVG sketches** from `partwright sketch`. Aim it straight at this folder:

      partwright sketch --dest reference

  Precise-mode SVGs carry a real millimeter scale in their metadata; treat
  those dimensions as authoritative.
- **Reference photos or screenshots** (PNG / JPG) of the thing being modeled,
  or of parts it has to mate with.

`CLAUDE.md` tells the build agent to read this folder before implementing
`build_part` and to reconcile the geometry against whatever it finds here.
