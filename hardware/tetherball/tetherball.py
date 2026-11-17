#!/usr/bin/env python3
"""
Tetherball pinball toy: parametric CadQuery model.

Units are mm.  World frame: z = 0 is the playfield TOP surface, +x is where the
arm points at hub angle 0.  Hub angle 0 is the UPPER stop; the hub turns
2 * turns_each_way * 360 deg to the lower stop.  Neutral (cord unwrapped) is
turns_each_way * 360, a whole number of turns, so the rotating parts look the
same at neutral as at angle 0 and only the nut moves.

    python tetherball.py export   [--set name=value ...]   STEP + STL files
    python tetherball.py check    [--set name=value ...]   interference tests
    python tetherball.py info     [--set name=value ...]   derived dimensions

Outputs:
    step/<part>.step            each part, positioned as assembled at neutral
    step/tetherball_assembly.step   everything incl. bought parts, coloured
    stl/<part>.stl              each printed part in its print orientation
"""
from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass, fields, replace
from pathlib import Path

import cadquery as cq
from cadquery import Solid, Vector, Wire

HERE = Path(__file__).resolve().parent
O = Vector(0, 0, 0)
X = Vector(1, 0, 0)
Y = Vector(0, 1, 0)
Z = Vector(0, 0, 1)
EPS = 0.01


@dataclass(frozen=True)
class Params:
    # playfield
    pf_thick: float = 19.05      # 3/4" playfield
    pf_hole_d: float = 32        # drill 1-1/4"
    # tetherball geometry
    ball_d: float = 32           # studded ball diameter
    ball_z: float = 19           # ball centre height (pinball centre is 13.5)
    arm_r: float = 50            # pole axis -> ball centre
    arm_d: float = 5             # steel arm rod
    pole_h: float = 70           # top of pole above playfield (check glass!)
    sleeve_d: float = 14         # visible pole diameter (what the cord wraps on)
    # turn limit
    turns_each_way: int = 4
    pitch: float = 3             # lead of the travelling-nut screw
    thread_r: float = 20         # screw major radius
    thread_e: float = 1.0        # eccentricity of screw profile (depth = 2e)
    thread_clear: float = 0.35   # radial clearance nut <-> screw
    nut_h: float = 14
    tooth_h: float = 2.0         # printed stop teeth on hub ring / stop collar
    tooth_w: float = 30          # printed tooth arc, degrees
    striker_h: float = 3.0       # M3 socket-cap head height (nut strikers)
    striker_d: float = 5.5
    stop_c: float = 0.6          # running clearance for tooth tips
    dog_r: float = 23.5          # radius of stop teeth / strikers
    big_d: float = 52            # OD of nut, hub ring, stop collar
    # encoder
    slots: int = 8
    disc_od: float = 70
    disc_t: float = 1.6
    slot_r0: float = 29.5
    slot_r1: float = 33.5
    # hardware
    brg_od: float = 22           # 608 bearing
    brg_w: float = 7
    brg_fit: float = 0.15
    race_land: float = 11.5      # OD of parts that may only touch an inner race
    outer_clear_d: float = 19.5  # ID of parts that may only touch an outer race
    pole_od: float = 8
    insert_d: float = 4.0        # M3 heat-set insert hole
    insert_l: float = 6
    m3_clear: float = 3.4
    collar_w: float = 9          # 8 mm shaft collar width
    washer_t: float = 1


# ------------------------------------------------------------------ helpers
def cyl(d, h, z0=0.0, x=0.0, y=0.0):
    return Solid.makeCylinder(d / 2, h, Vector(x, y, z0), Z)


def cyl_x(d, h, x0, y, z):
    """Cylinder along +x starting at x0."""
    return Solid.makeCylinder(d / 2, h, Vector(x0, y, z), X)


def cone(d1, d2, h, z0, x=0.0, y=0.0):
    return Solid.makeCone(d1 / 2, d2 / 2, h, Vector(x, y, z0), Z)


def box(x0, y0, z0, dx, dy, dz):
    return Solid.makeBox(dx, dy, dz, Vector(x0, y0, z0))


def rotz(s, a):
    return s.rotate(O, Z, a)


def ring(od, id_, z0, h):
    return cyl(od, h, z0).cut(cyl(id_, h + 2, z0 - 1))


def arc_block(r0, r1, a0, a1, z0, h):
    s = Solid.makeCylinder(r1, h, Vector(0, 0, z0), Z, a1 - a0)
    if r0 > 0:
        s = s.cut(cyl(2 * r0, h + 2, z0 - 1))
    return rotz(s, a0)


def tidy(s):
    """Merge coplanar faces, but only keep the result if it is still a valid
    solid: OCCT's clean() occasionally corrupts fused shapes.  Single-solid
    compounds are unwrapped so STEP files contain plain solids."""
    try:
        c = s.clean()
        if c.isValid():
            s = c
    except Exception:
        pass
    if isinstance(s, cq.Compound):
        solids = s.Solids()
        if len(solids) == 1:
            s = solids[0]
    return s


def fuse(*shapes):
    return tidy(shapes[0].fuse(*shapes[1:])) if len(shapes) > 1 else shapes[0]


# ------------------------------------------------------------------ model
class Tetherball:
    def __init__(self, p: Params = Params()):
        self.p = p
        P = p
        self.N = P.turns_each_way
        self.theta_tot = 2 * self.N * 360
        self.k_lead = 360 / P.pitch
        self.g_stop = max(P.striker_h, P.tooth_h) + P.stop_c
        if P.tooth_h + P.striker_h + P.stop_c > self.g_stop + P.pitch:
            raise ValueError("stop teeth too tall for this pitch: they would collide one turn early")
        self.beta = math.degrees(math.asin((P.striker_d / 2) / P.dog_r))

        # upper hub (above playfield)
        self.hub_bot, self.hub_top, self.hub_d = 1.5, 29.5, 46
        self.tube_od, self.hub_bore = 26, 13
        self.top_brg_z = self.hub_top - P.brg_w
        # lower hub (below playfield)
        self.lh_top = -P.pf_thick - 2
        self.socket_d, self.socket_dp = 46, 10
        self.tube_bot = self.lh_top - self.socket_dp
        self.disc_bot = self.lh_top - 14
        self.ring_t = 3
        self.sh_z = self.disc_bot - self.ring_t
        self.nut_top_up = self.sh_z - self.g_stop
        self.nut_bot_up = self.nut_top_up - P.nut_h
        self.travel = self.theta_tot / self.k_lead
        self.c_top = self.nut_bot_up - self.travel - self.g_stop
        self.c_t = 5
        self.spacer_len = self.top_brg_z - (self.c_top + P.brg_w) - 0.2
        # bracket
        self.wall_in, self.wall_t = -39, 5
        self.wall_out = self.wall_in - self.wall_t
        self.fl_t, self.fl_half = 5, 44
        self.bp_top = self.c_top - P.washer_t - P.collar_w - 1.5
        self.bp_t = 6
        self.bp_bot = self.bp_top - self.bp_t
        self.clamp_h = 14
        self.tab_w = self.tab_h = 5
        self.tab_end_x = self.wall_out - 6
        self.tab_z_up = self.nut_bot_up + self.tab_h / 2
        self.tab_z_low = self.tab_z_up - self.travel
        # bought parts
        self.pole_top = P.pole_h - 8
        self.pole_bot = self.bp_bot - self.clamp_h - 10
        self.rod_len = P.arm_r - 7 - 11
        # patterns
        self.collar_screw_a = [0, 110, 230]   # uneven: collar fits one way only
        self.collar_screw_r = 14.5
        self.socket_screw_a = [30, 150, 270]
        self.collar_a0 = -self.beta - P.tooth_w

    # -------------------------------------------------------------- info
    def info(self):
        return {
            "pole tube length (8 mm OD stainless)": self.pole_top - self.pole_bot,
            "arm rod length (5 mm steel)": self.rod_len,
            "spacer length": self.spacer_len,
            "depth below playfield underside (incl. pole tail)": -self.pole_bot - self.p.pf_thick,
            "nut travel": self.travel,
            "stop-to-stop turns": self.theta_tot / 360,
        }

    # -------------------------------------------------------------- screw
    def helix(self, z0, z1, add=0.0):
        """Helical lobe screw: circle of radius (thread_r - e + add) offset by e,
        swept along a right-hand helix.  Phase depends only on world z
        (eccentric direction = 360 * z / pitch), so screw and nut always agree."""
        P = self.p
        L = z1 - z0
        w = Wire.makeCircle(P.thread_r - P.thread_e + add, Vector(P.thread_e, 0, 0), Z)
        s = Solid.extrudeLinearWithRotation(w, [], O, Vector(0, 0, L), 360 * L / P.pitch)
        return rotz(s, 360 * z0 / P.pitch).translate(Vector(0, 0, z0))

    # -------------------------------------------------------------- parts (world position, hub angle 0, nut at upper stop)
    def upper_hub(self):
        P = self.p
        s = fuse(cyl(self.hub_d, self.hub_top - self.hub_bot, self.hub_bot),
                 cyl(self.tube_od, self.hub_bot - self.tube_bot + EPS, self.tube_bot))
        cuts = [
            cyl(self.hub_bore, 200, self.tube_bot - 1),
            cyl(P.brg_od + P.brg_fit, P.brg_w + 1, self.top_brg_z),
            cyl(P.outer_clear_d, 1.5 + EPS, self.top_brg_z - 1.5),
            cyl_x(P.arm_d + 0.15, 30, 11, 0, P.ball_z),                       # arm socket
            cyl(3.2, 30, P.ball_z, 16.5),                                      # set screw
            cyl(P.insert_d, P.insert_l + 1, self.hub_top - P.insert_l, 16.5),
        ]
        for a in self.socket_screw_a:   # radial inserts in the tube end
            cuts.append(rotz(cyl_x(P.insert_d, 10, self.tube_od / 2 - 5.5, 0,
                                   self.tube_bot + self.socket_dp / 2), a))
        return tidy(s.cut(*cuts))

    def lower_hub(self):
        P = self.p
        s = fuse(cyl(self.socket_d, self.lh_top - self.disc_bot + EPS, self.disc_bot - EPS),
                 cyl(P.big_d, self.ring_t, self.sh_z),
                 self.helix(self.c_top, self.sh_z + EPS),
                 arc_block(P.dog_r - 2.5, P.big_d / 2, self.beta, self.beta + P.tooth_w,
                           self.sh_z - P.tooth_h, P.tooth_h + EPS))
        zs = self.tube_bot + self.socket_dp / 2
        cuts = [
            cyl(self.tube_od + 0.3, self.socket_dp + 1, self.tube_bot),
            cyl(self.hub_bore, 200, self.c_top - 1),
            cyl(P.brg_od + P.brg_fit, P.brg_w + 1, self.c_top - 1),
            cyl(P.outer_clear_d, 1.5, self.c_top + P.brg_w - EPS),
            box(-1, -1, -5, 2, 2, 10).rotate(O, Z, 45)
                .translate(Vector(self.socket_d / 2, 0, self.lh_top - 4)),   # index notch at +x
        ]
        for a in self.socket_screw_a:
            cuts.append(rotz(fuse(cyl_x(P.m3_clear, 40, 0, 0, zs), cyl_x(6, 10, 19, 0, zs)), a))
        for a in self.collar_screw_a:
            cuts.append(rotz(cyl(P.insert_d, P.insert_l + 1, self.c_top - 1, self.collar_screw_r), a))
        return tidy(s.cut(*cuts))

    def encoder_disc(self):
        P = self.p
        s = ring(P.disc_od, self.socket_d + 0.3, self.disc_bot, P.disc_t)
        cuts = [arc_block(P.slot_r0, P.slot_r1, i * 360 / P.slots, i * 360 / P.slots + 180 / P.slots,
                          self.disc_bot - 1, P.disc_t + 2) for i in range(P.slots)]
        return tidy(s.cut(*cuts))

    def nut_at(self, z_bot):
        P = self.p
        s = fuse(cyl(P.big_d, P.nut_h, z_bot),
                 # anti-rotation tab, flush with the bottom face so it prints on the bed
                 box(self.tab_end_x, -self.tab_w / 2, z_bot,
                     -self.tab_end_x - P.big_d / 2 + 3, self.tab_w, self.tab_h))
        cuts = [
            self.helix(z_bot - 1, z_bot + P.nut_h + 1, P.thread_clear),
            cyl(P.insert_d, P.insert_l + 1, z_bot + P.nut_h - P.insert_l, P.dog_r),
            cyl(P.insert_d, P.insert_l + 1, z_bot - 1, P.dog_r),
            cone(2 * P.thread_r + 2, 2 * P.thread_r - 2, 2, z_bot - EPS),
            cone(2 * P.thread_r - 2, 2 * P.thread_r + 2, 2, z_bot + P.nut_h - 2 + EPS),
        ]
        return tidy(s.cut(*cuts))

    def nut(self):
        return self.nut_at(self.nut_bot_up)

    def strikers_at(self, z_bot):
        """The two M3 socket-head strikers (kept as separate solids)."""
        P = self.p
        return [cyl(P.striker_d, P.striker_h, z_bot + P.nut_h, P.dog_r),
                cyl(P.striker_d, P.striker_h, z_bot - P.striker_h, P.dog_r)]

    def stop_collar(self):
        P = self.p
        s = fuse(ring(P.big_d, P.outer_clear_d, self.c_top - self.c_t, self.c_t),
                 arc_block(P.dog_r - 2.5, P.big_d / 2, self.collar_a0, self.collar_a0 + P.tooth_w,
                           self.c_top - EPS, P.tooth_h + EPS))
        cuts = [rotz(fuse(cyl(P.m3_clear, self.c_t + 2, self.c_top - self.c_t - 1, self.collar_screw_r),
                          cyl(6, 4, self.c_top - self.c_t - 1, self.collar_screw_r)), a)
                for a in self.collar_screw_a]
        return tidy(s.cut(*cuts))

    def spacer(self):
        P = self.p
        return ring(P.race_land, P.pole_od + 0.3, self.c_top + P.brg_w + 0.1, self.spacer_len)

    def washer(self):
        P = self.p
        return ring(P.race_land, P.pole_od + 0.3, self.c_top - P.washer_t, P.washer_t)

    def pole_sleeve(self):
        P = self.p
        base_d, base_top, ht = 20, 40, self.hub_top
        s = fuse(cyl(P.race_land, 1 + EPS, ht),                     # inner-race-only foot
                 cyl(base_d, base_top - ht - 1, ht + 1),
                 cone(base_d, P.sleeve_d, 3, base_top - EPS),
                 cyl(P.sleeve_d, P.pole_h - base_top - 2, base_top),
                 cone(P.sleeve_d, P.sleeve_d - 4, 2, P.pole_h - 2))
        fairlead = cyl(9, 3.6, P.pole_h - 3.5).cut(
            Solid.makeTorus(4.5, 3.25, Vector(0, 0, P.pole_h - 3.5), Z))
        cuts = [
            cyl(P.pole_od + 0.15, self.pole_top - ht + 1, ht - 1),
            cyl(4.2, 5, self.pole_top - EPS),                         # PTFE liner
            fairlead,
            cyl(2.6, 5, P.pole_h - 4),
            cyl_x(P.insert_d, 20, 0, 0, ht + 6),                      # set screw insert
        ]
        return tidy(s.cut(*cuts))

    def ball_local(self):
        """Studded ball, centre at origin, hub toward -x."""
        P = self.p
        R = P.ball_d / 2
        s = Solid.makeSphere(R, O, Z, -90, 90, 360)
        stud0 = fuse(cyl(5, 2, 0), cone(5, 3, 1.2, 2)).rotate(O, Y, 90)   # axis along +x
        n, golden = 40, 180 * (3 - math.sqrt(5))
        studs = []
        for i in range(n):
            z = 1 - 2 * (i + 0.5) / n
            lon, lat = i * golden, math.degrees(math.asin(z))
            if z > 0.8 or math.cos(math.radians(lat)) * math.cos(math.radians(lon)) < -0.8:
                continue   # leave room for the cord (top) and arm (-x)
            studs.append(stud0.translate(Vector(R - 0.5, 0, 0)).rotate(O, Y, -lat).rotate(O, Z, lon))
        s = tidy(s.fuse(*studs))
        cuts = [
            cyl_x(P.arm_d + 0.15, R - 1, -R - 1, 0, 0),     # arm socket (rod goes 9 mm in)
            cyl(2.4, R + 1, 0, -4),                          # cord hole from the top
            Solid.makeSphere(2.75, Vector(-4, 0, 0), Z, -90, 90, 360),   # knot pocket
        ]
        return tidy(s.cut(*cuts))

    def ball(self):
        return self.ball_local().translate(Vector(self.p.arm_r, 0, self.p.ball_z))

    def bracket(self):
        P = self.p
        zf, wo = -P.pf_thick, self.wall_out
        h = zf - self.bp_bot
        s = fuse(
            box(wo, -self.fl_half, zf - self.fl_t, self.fl_half - wo, 2 * self.fl_half, self.fl_t),  # flange
            box(wo, -self.fl_half + 10, self.bp_bot, self.wall_t, 2 * self.fl_half - 20, h),         # back wall
            box(wo, -self.fl_half + 10, self.bp_bot, 14 - wo, 2 * self.fl_half - 20, self.bp_t),     # bottom plate
            cyl(20, self.clamp_h + EPS, self.bp_bot - self.clamp_h),                                  # pole clamp
            box(self.wall_in - EPS, 29, self.bp_bot, -self.wall_in - 26 + EPS, 5, h),                 # ribs
            box(self.wall_in - EPS, -34, self.bp_bot, -self.wall_in - 26 + EPS, 5, h),
        )
        cuts = [
            # U-shaped opening, open toward +x so the bracket slides on from the front
            fuse(cyl(P.big_d, self.fl_t + 2, zf - self.fl_t - 1),
                 box(0, -P.big_d / 2, zf - self.fl_t - 1, 100, P.big_d, self.fl_t + 2)),
            cyl(P.pole_od + 0.15, 100, self.bp_bot - self.clamp_h - 1),
        ]
        for a in (0, 90):   # clamp set-screw inserts
            cuts.append(rotz(cyl_x(P.insert_d, 20, 0, 0, self.bp_bot - self.clamp_h / 2), a))
        for x, y in ((-31, 38), (-31, -38), (34, 38), (34, -38)):   # #6 wood screws, countersunk
            cuts += [cyl(3.8, self.fl_t + 1, zf - self.fl_t - EPS, x, y),
                     cone(8, 3.8, 2.2, zf - self.fl_t - EPS, x, y)]
        # opto slots: 90 +/- (45 + 45/4)/2 deg (quadrature for 8 slots), +/- 8 deg adjust
        for a in (90 - 28.125, 90 + 28.125):
            cuts.append(arc_block(39 - 1.7, 39 + 1.7, a - 8, a + 8, zf - self.fl_t - 1, self.fl_t + 2))
        # slot for the nut tab
        cuts.append(box(wo - 1, -self.tab_w / 2 - 0.5, self.tab_z_low - self.tab_h / 2 - 2,
                        self.wall_t + 2, self.tab_w + 1, self.travel + self.tab_h + 4))
        # micro-switch M2 slots: upper switch +y, lower switch -y, levers over the tab slot
        for zc, sg in ((self.tab_z_up + self.tab_h / 2 + 7, 1), (self.tab_z_low - self.tab_h / 2 - 7, -1)):
            for yy in (sg * 6, sg * 15.5):
                cuts += [box(wo - 1, yy - 1.1, zc - 4, self.wall_t + 2, 2.2, 8),
                         cyl_x(2.2, self.wall_t + 2, wo - 1, yy, zc - 4),
                         cyl_x(2.2, self.wall_t + 2, wo - 1, yy, zc + 4)]
        return tidy(s.cut(*cuts))

    # -------------------------------------------------------------- reference geometry
    def playfield(self):
        P = self.p
        return box(-80, -80, -P.pf_thick, 160, 160, P.pf_thick).cut(
            cyl(P.pf_hole_d, P.pf_thick + 2, -P.pf_thick - 1))

    def shaft_collar(self):
        P = self.p
        return ring(16, P.pole_od, self.c_top - P.washer_t - P.collar_w, P.collar_w)

    def bought_parts(self):
        P = self.p
        return {
            "pole_tube": ring(P.pole_od, 6, self.pole_bot, self.pole_top - self.pole_bot),
            "arm_rod": cyl_x(P.arm_d, self.rod_len, 11, 0, P.ball_z),
            "bearing_top": ring(P.brg_od, P.pole_od, self.top_brg_z, P.brg_w),
            "bearing_bottom": ring(P.brg_od, P.pole_od, self.c_top, P.brg_w),
            "shaft_collar": self.shaft_collar(),
        }


# ------------------------------------------------------------------ printed-part registry
ROTATING = ["upper_hub", "lower_hub", "encoder_disc", "stop_collar", "ball"]
PRINTED = ["upper_hub", "lower_hub", "encoder_disc", "nut", "stop_collar", "bracket",
           "pole_sleeve", "spacer", "washer", "ball"]
_RGB = {"red": (0.95, 0.38, 0.28), "gold": (0.95, 0.80, 0.10), "blue": (0.27, 0.51, 0.71),
        "light": (0.80, 0.80, 0.80), "white": (0.97, 0.97, 0.97), "pale": (0.68, 0.85, 0.90),
        "orange": (1.0, 0.65, 0.0), "steel": (0.75, 0.75, 0.78), "dark": (0.40, 0.40, 0.42)}
COLORS = {"upper_hub": "red", "lower_hub": "red", "stop_collar": "red",
          "encoder_disc": "gold", "nut": "blue", "bracket": "light",
          "pole_sleeve": "white", "spacer": "pale", "washer": "pale",
          "ball": "orange", "strikers": "steel", "pole_tube": "steel", "arm_rod": "dark",
          "bearing_top": "dark", "bearing_bottom": "dark", "shaft_collar": "steel"}


def color(name):
    return cq.Color(*_RGB[COLORS[name]])


def print_pose(m: Tetherball, name: str, s):
    """Move a world-positioned part into its recommended print orientation."""
    P = m.p
    t = lambda z: Vector(0, 0, z)
    if name == "upper_hub":    return s.rotate(O, X, 180).translate(t(m.hub_top))      # collar face down
    if name == "lower_hub":    return s.rotate(O, X, 180).translate(t(m.lh_top))       # socket face down
    if name == "encoder_disc": return s.translate(t(-m.disc_bot))
    if name == "nut":          return s.translate(t(-m.nut_bot_up))
    if name == "stop_collar":  return s.translate(t(-(m.c_top - m.c_t)))
    if name == "bracket":      return s.translate(Vector(-m.wall_out, 0, 0)).rotate(O, Y, -90)  # back wall down
    if name == "pole_sleeve":  return s.translate(t(-m.hub_top))
    if name == "spacer":       return s.translate(t(-(m.c_top + P.brg_w + 0.1)))
    if name == "washer":       return s.translate(t(-(m.c_top - P.washer_t)))
    if name == "ball":         return m.ball_local().rotate(O, Y, -90).translate(t(P.ball_d / 2))  # arm socket down
    raise KeyError(name)


def neutral_pose(m: Tetherball, name: str, s):
    """Parts as assembled at neutral: rotating parts are at 0 mod 360, the nut is mid-travel."""
    if name in ("nut", "strikers"):
        return s.translate(Vector(0, 0, -m.N * 360 / m.k_lead))
    return s


def write_step(shape, path: Path) -> str:
    """Write a part as STEP and prove it re-imports as one valid solid of the
    same volume.  With parameter-space curves (pcurves) OCCT's writer mangles
    the studded ball's sphere face (31 trimming loops): it reads back as 30
    loose solids.  pcurves are optional in STEP and CAD importers rebuild them,
    so any part that fails is rewritten without them and checked again."""
    for opt in ({}, {"write_pcurves": False}):
        cq.exporters.export(shape, str(path), opt=opt)
        r = cq.importers.importStep(str(path)).val()
        if (len(r.Solids()) == 1 and r.isValid()
                and abs(r.Volume() - shape.Volume()) < 1e-3 * shape.Volume()):
            return "verified" + (", no pcurves" if opt else "")
    raise RuntimeError(f"{path.name} failed STEP round-trip: {len(r.Solids())} solids, "
                       f"valid={r.isValid()}, volume {r.Volume():.1f} vs {shape.Volume():.1f}")


# ------------------------------------------------------------------ commands
def cmd_export(m: Tetherball):
    step_dir, stl_dir = HERE / "step", HERE / "stl"
    step_dir.mkdir(exist_ok=True)
    stl_dir.mkdir(exist_ok=True)
    assy = cq.Assembly(name="tetherball")
    for name in PRINTED:
        s = getattr(m, name)()
        placed = neutral_pose(m, name, s)
        how = write_step(placed, step_dir / f"{name}.step")
        cq.exporters.export(print_pose(m, name, s), str(stl_dir / f"{name}.stl"),
                            tolerance=0.02, angularTolerance=0.15)
        assy.add(placed, name=name, color=color(name))
        print(f"  {name:13s} -> step/{name}.step ({how}), stl/{name}.stl")
    for i, st in enumerate(m.strikers_at(m.nut_bot_up)):
        assy.add(neutral_pose(m, "strikers", st), name=f"striker_{'top' if i == 0 else 'bottom'}",
                 color=color("strikers"))
    for name, s in m.bought_parts().items():
        assy.add(s, name=name, color=color(name))
    # pcurves off for the same reason as write_step(); verify every solid came back
    ap = step_dir / "tetherball_assembly.step"
    assy.export(str(ap), write_pcurves=False)
    back = cq.importers.importStep(str(ap)).val().Solids()
    expected = len(PRINTED) + 2 + len(m.bought_parts())
    if len(back) != expected or not all(x.isValid() for x in back):
        raise RuntimeError(f"assembly STEP round-trip: {len(back)} solids (expected {expected})")
    print(f"  assembly      -> step/tetherball_assembly.step (verified, {len(back)} solids)")


def cmd_check(m: Tetherball) -> int:
    """Interference tests for the travelling-nut stop and bracket clearances."""
    print("building parts...", flush=True)
    lh, sc = m.lower_hub(), m.stop_collar()
    nut, stk = m.nut(), m.strikers_at(m.nut_bot_up)
    moving_extra = [m.upper_hub(), m.encoder_disc(), m.ball()]
    fixed = [m.bracket(), m.playfield(), m.shaft_collar()]
    bad = [n for n, x in (("lower_hub", lh), ("stop_collar", sc), ("nut", nut), ("bracket", fixed[0]))
           + tuple((f"moving_{i}", x) for i, x in enumerate(moving_extra)) if not x.isValid()]
    if bad:
        print("INVALID SOLIDS (booleans would be meaningless):", ", ".join(bad))
        return 1

    def overlap(a_list, b_list):
        v = 0.0
        for a in a_list:
            for b in b_list:
                p, q = a.BoundingBox(), b.BoundingBox()
                if (p.xmax < q.xmin or q.xmax < p.xmin or p.ymax < q.ymin or q.ymax < p.ymin
                        or p.zmax < q.zmin or q.zmax < p.zmin):
                    continue
                # Distance first: OCCT's boolean common sometimes returns a whole
                # solid for parts that are clearly apart (seen with the helical
                # screw), while the distance query is reliable.
                if a.distance(b) > 1e-4:
                    continue
                v += a.intersect(b).Volume()
        return v

    def pose(a, wrong=False):
        dz = (1 if wrong else -1) * a / m.k_lead
        rot = [rotz(lh, a), rotz(sc, a)]
        nuts = [x.translate(Vector(0, 0, dz)) for x in [nut] + stk]
        return rot, nuts

    N, T = m.N, m.theta_tot
    cases = [
        ("screw/nut mesh, mid-travel", 90 + N * 360, False, "clear"),
        ("screw/nut mesh, odd angle (1337 deg)", 1337, False, "clear"),
        ("sanity: nut moved the WRONG way collides", 90 + N * 360, True, "hit"),
        ("upper stop: at contact", 0, False, "clear"),
        ("upper stop: 3 deg past contact is blocked", -3, False, "hit"),
        ("one turn before upper stop: teeth pass", 360, False, "clear"),
        ("lower stop: at contact", T, False, "clear"),
        ("lower stop: 3 deg past contact is blocked", T + 3, False, "hit"),
        ("one turn before lower stop: teeth pass", T - 360, False, "clear"),
    ]
    fails = 0
    for name, a, wrong, expect in cases:
        rot, nuts = pose(a, wrong)
        v = overlap(rot, nuts)
        got = "hit" if v > 1e-3 else "clear"
        ok = got == expect
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'} {name:46s} expect {expect:5s} got {got:5s} ({v:.4f} mm^3)", flush=True)
    for name, a in (("upper stop", 0), ("neutral", N * 360 + 45), ("lower stop", T)):
        rot, nuts = pose(a)
        movers = rot + nuts + [rotz(s, a) for s in moving_extra]
        v = overlap(movers, fixed)
        ok = v <= 1e-3
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'} {'bracket/playfield clearance at ' + name:46s} expect clear got "
              f"{'clear' if ok else 'hit':5s} ({v:.4f} mm^3)", flush=True)
    # the clearance test must be able to see a collision: shrink the playfield hole
    tight = Tetherball(replace(m.p, pf_hole_d=24))
    v = overlap([m.upper_hub()], [tight.playfield()])
    ok = v > 1e-3
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'} {'sanity: undersized playfield hole collides':46s} expect hit   got "
          f"{'hit' if ok else 'clear':5s} ({v:.4f} mm^3)")
    print("ALL PASS" if not fails else f"{fails} FAILED")
    return 1 if fails else 0


def parse_params(sets):
    p = Params()
    types = {f.name: f.type for f in fields(Params)}
    for kv in sets or []:
        k, v = kv.split("=", 1)
        if k not in types:
            sys.exit(f"unknown parameter {k!r}; choose from: {', '.join(types)}")
        p = replace(p, **{k: int(v) if types[k] in (int, "int") else float(v)})
    return p


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["export", "check", "info"])
    ap.add_argument("--set", action="append", metavar="NAME=VALUE", help="override a parameter")
    a = ap.parse_args()
    m = Tetherball(parse_params(a.set))
    for k, v in m.info().items():
        print(f"  {k}: {v:g} mm" if "turns" not in k else f"  {k}: {v:g}")
    if a.command == "export":
        cmd_export(m)
    elif a.command == "check":
        sys.exit(cmd_check(m))


if __name__ == "__main__":
    main()
