#!/usr/bin/env python3
"""
Tetherball pinball toy: parametric CadQuery model (slim layout).

A thin pole that never turns stands on the playfield. A real cord comes out of
its top and is tied to a smooth ball. The ball rides on a low steel arm that
circles the pole, so the cord wraps around the pole like a tetherball rope. All
bearings and the turn-limit mechanism sit under the playfield. Above it, the
only moving parts are a steel shaft collar on a thin rotating tube, the arm and
the ball.

Units are mm. World frame: z = 0 is the playfield TOP surface, +x is where the
arm points at hub angle 0. Hub angle 0 is the UPPER stop (fully wrapped one
way). The hub turns 2 * turns_each_way * 360 deg to the lower stop. Neutral
(cord hanging straight) is turns_each_way * 360, a whole number of turns, so the
rotating parts look the same at neutral as at either stop; only the nut and the
cord differ.

    python tetherball.py export   [--set name=value ...]   STEP + STL files
    python tetherball.py check    [--set name=value ...]   interference tests
    python tetherball.py info     [--set name=value ...]   cut lengths etc.

Outputs:
    step/<part>.step                     each printed part, positioned as assembled
    step/tetherball_assembly.step        everything incl. bought parts + cord, at neutral
    step/tetherball_assembly_wrapped.step  same, wound fully one way (cord coiled)
    stl/<part>.stl                       each printed part in its print orientation
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
    pf_hole_d: float = 10        # clearance for the rotating tube (drill 3/8" + a touch, or 10 mm)
    # what you see above the playfield
    ball_d: float = 32           # smooth ball
    ball_z: float = 17.5         # ball centre height (bottom clears the playfield by 1.5)
    arm_r: float = 50            # pole axis -> ball centre
    arm_z: float = 11.5          # arm height (centre of the tapped hole in the shaft collar)
    arm_d: float = 5             # M5 threaded rod (stainless)
    pole_h: float = 70           # top of pole above playfield (check glass/ramp clearance!)
    sleeve_d: float = 9.5        # visible pole diameter (what the cord wraps on)
    cord_d: float = 1.5          # braided cord
    # bought tubes / collar
    tube_od: float = 8           # rotating tube (stainless 8 x 6), rides in the 608 bearings
    tube_id: float = 6
    pole_od: float = 5           # fixed pole (stainless or brass 5 x 3), cord runs inside
    pole_id: float = 3
    collar_od: float = 16        # 8 mm shaft collar, drilled & tapped M5 for the arm
    collar_w: float = 9
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
    body_d: float = 46           # lower-hub body (encoder disc slides over it); keeps the
                                 # stop ring's overhang to 3 mm when printed upside down
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
    race_land: float = 11.5      # OD of rotating parts that touch an inner race
    race_relief_d: float = 17    # ID of fixed parts next to a bearing (outer race only)
    bore_fit: float = 0.15       # printed bores over the 8 mm tube
    insert_d: float = 4.0        # M3 heat-set insert hole
    insert_l: float = 6
    m3_clear: float = 3.4
    m5_insert_d: float = 6.4     # M5 heat-set insert hole (in the ball)
    m5_insert_l: float = 6


# ------------------------------------------------------------------ helpers
def cyl(d, h, z0=0.0, x=0.0, y=0.0):
    return Solid.makeCylinder(d / 2, h, Vector(x, y, z0), Z)


def cyl_x(d, h, x0, y, z):
    """Cylinder along +x starting at x0."""
    return Solid.makeCylinder(d / 2, h, Vector(x0, y, z), X)


def cyl_between(d, a: Vector, b: Vector):
    return Solid.makeCylinder(d / 2, (b - a).Length, a, (b - a).normalized())


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
    solid: OCCT's clean() occasionally corrupts fused shapes. Single-solid
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
        if P.ball_z - P.ball_d / 2 < 1:
            raise ValueError("ball would touch the playfield")
        if P.arm_z - P.collar_w / 2 < 1:
            raise ValueError("shaft collar would touch the playfield")
        self.bore = P.tube_od + P.bore_fit

        # above the playfield
        self.collar_z0 = P.arm_z - P.collar_w / 2
        self.tube_top = self.collar_z0 + P.collar_w          # flush with the collar top
        self.sleeve_bot = self.tube_top + 0.8
        self.pole_top = P.pole_h - 4

        # bracket flange with the top bearing (pocket opens downward)
        T = P.pf_thick
        self.fl_t = 9
        self.flange_bot = -T - self.fl_t
        self.brg1_top = self.flange_bot + P.brg_w            # = -T - 2
        # lower hub (clamped on the tube between the bearings)
        self.lh_top = self.flange_bot - 0.3                  # inner-race boss, 0.3 below the bearing
        self.body_top = self.lh_top - 0.7
        self.disc_top = self.flange_bot - 9                  # room above the disc for the optos
        self.disc_bot = self.disc_top - P.disc_t
        self.ring_t = 3
        self.sh_z = self.disc_bot - self.ring_t
        self.set_z = (self.body_top + self.disc_top) / 2     # lower-hub set screws
        self.nut_top_up = self.sh_z - self.g_stop
        self.nut_bot_up = self.nut_top_up - P.nut_h
        self.travel = self.theta_tot / self.k_lead
        self.c_top = self.nut_bot_up - self.travel - self.g_stop
        self.c_t = 5
        # bottom bearing (in the bracket's bottom plate), carries the weight
        self.brg2_top = self.c_top - self.c_t - 1
        self.brg2_bot = self.brg2_top - P.brg_w
        self.tube_bot = self.brg2_bot
        # bracket
        self.wall_in, self.wall_t = -39, 5
        self.wall_out = self.wall_in - self.wall_t
        self.fl_half = 44
        self.bp_top = self.brg2_top - 1
        self.bp_bot = self.brg2_bot - 7
        self.clamp_h = 14
        self.tab_w = self.tab_h = 5
        self.tab_end_x = self.wall_out - 6
        self.tab_z_up = self.nut_bot_up + self.tab_h / 2
        self.tab_z_low = self.tab_z_up - self.travel
        self.pole_bot = self.bp_bot - self.clamp_h - 10
        # arm: M5 rod from the tube surface (it also bears on the tube) into the ball's insert
        self.arm_end_x = P.arm_r - 3
        self.rod_len = self.arm_end_x - P.tube_od / 2
        # patterns
        self.collar_screw_a = [0, 110, 230]   # uneven: stop collar fits one way only
        self.collar_screw_r = 14.5
        self.set_screw_a = [0, 270]           # lower-hub set screws onto tube flats
        self.collar_a0 = -self.beta - P.tooth_w

    # -------------------------------------------------------------- info
    def info(self):
        P = self.p
        straight = (Vector(P.arm_r, 0, P.ball_z + P.ball_d / 2) - Vector(0, 0, P.pole_h)).Length
        return {
            "rotating tube 8x6, length": self.tube_top - self.tube_bot,
            "fixed pole 5x3, length": self.pole_top - self.pole_bot,
            "arm, M5 threaded rod, length": self.rod_len,
            "tube flat for the shaft collar, from tube top": self.tube_top - P.arm_z,
            "tube flats for the lower hub, from tube top": self.tube_top - self.set_z,
            "cord used per wrap": math.pi * (P.sleeve_d + P.cord_d),
            "cord pulled out of the pole at full wrap": self.N * math.pi * (P.sleeve_d + P.cord_d),
            "cord, pole top to ball at neutral": straight,
            "depth below playfield underside (incl. pole tail)": -self.pole_bot - P.pf_thick,
            "nut travel": self.travel,
            "stop-to-stop turns": self.theta_tot / 360,
        }

    # -------------------------------------------------------------- screw
    def helix(self, z0, z1, add=0.0):
        """Helical lobe screw: circle of radius (thread_r - e + add) offset by e,
        swept along a right-hand helix. Phase depends only on world z
        (eccentric direction = 360 * z / pitch), so screw and nut always agree."""
        P = self.p
        L = z1 - z0
        w = Wire.makeCircle(P.thread_r - P.thread_e + add, Vector(P.thread_e, 0, 0), Z)
        s = Solid.extrudeLinearWithRotation(w, [], O, Vector(0, 0, L), 360 * L / P.pitch)
        return rotz(s, 360 * z0 / P.pitch).translate(Vector(0, 0, z0))

    # -------------------------------------------------------------- printed parts
    # (world position, hub angle 0, nut at the upper stop)
    def lower_hub(self):
        P = self.p
        s = fuse(cyl(P.race_land, self.lh_top - self.body_top + EPS, self.body_top - EPS),   # inner-race boss
                 cyl(P.body_d, self.body_top - self.disc_bot + EPS, self.disc_bot - EPS),
                 cyl(P.big_d, self.ring_t, self.sh_z),
                 self.helix(self.c_top, self.sh_z + EPS),
                 arc_block(P.dog_r - 2.5, P.big_d / 2, self.beta, self.beta + P.tooth_w,
                           self.sh_z - P.tooth_h, P.tooth_h + EPS))
        cuts = [
            cyl(self.bore, 300, self.c_top - 1),
            box(-1, -1, -5, 2, 2, 10).rotate(O, Z, 45)
                .translate(Vector(P.body_d / 2, 0, self.body_top)),      # index notch at +x
        ]
        for a in self.set_screw_a:   # M3 x 16 set screws onto flats on the tube
            cuts.append(rotz(fuse(cyl_x(3.2, P.body_d, 0, 0, self.set_z),
                                  cyl_x(P.insert_d, P.insert_l + 1, P.body_d / 2 - P.insert_l, 0, self.set_z)), a))
        for a in self.collar_screw_a:
            cuts.append(rotz(cyl(P.insert_d, P.insert_l + 1, self.c_top - 1, self.collar_screw_r), a))
        return tidy(s.cut(*cuts))

    def encoder_disc(self):
        P = self.p
        s = ring(P.disc_od, P.body_d + 0.3, self.disc_bot, P.disc_t)
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
        """The two M3 socket-head strikers (separate solids)."""
        P = self.p
        return [cyl(P.striker_d, P.striker_h, z_bot + P.nut_h, P.dog_r),
                cyl(P.striker_d, P.striker_h, z_bot - P.striker_h, P.dog_r)]

    def stop_collar(self):
        P = self.p
        zb = self.c_top - self.c_t
        s = fuse(cyl(P.big_d, self.c_t, zb),
                 cyl(P.race_land, 1 + EPS, zb - 1),                       # bottom bearing inner-race boss
                 arc_block(P.dog_r - 2.5, P.big_d / 2, self.collar_a0, self.collar_a0 + P.tooth_w,
                           self.c_top - EPS, P.tooth_h + EPS))
        cuts = [cyl(self.bore, 20, zb - 2)]
        cuts += [rotz(fuse(cyl(P.m3_clear, self.c_t + 2, zb - 1, self.collar_screw_r),
                           cyl(6, 4, zb - 1, self.collar_screw_r)), a) for a in self.collar_screw_a]
        return tidy(s.cut(*cuts))

    def tube_bushing(self):
        """Pressed into the top of the rotating tube; steadies the fixed pole."""
        P = self.p
        return ring(P.tube_id, P.pole_od + 0.2, self.tube_top - 8, 8)

    def pole_sleeve(self):
        """The visible pole. Glued onto the fixed pole tube."""
        P = self.p
        top = P.pole_h
        s = fuse(cyl(P.sleeve_d, top - 2 - self.sleeve_bot, self.sleeve_bot),
                 cone(P.sleeve_d, P.sleeve_d - 4, 2, top - 2 - EPS))
        flare = cyl(5.2, 2.0, top - 1.9).cut(Solid.makeTorus(2.6, 1.6, Vector(0, 0, top - 1.9), Z))
        cuts = [
            cyl(P.pole_od + 0.15, self.pole_top - self.sleeve_bot + 1, self.sleeve_bot - 1),
            cyl(2.0, 10, self.pole_top - EPS),            # cord channel above the pole tube
            flare,                                         # rounded cord exit (fairlead)
        ]
        return tidy(s.cut(*cuts))

    def ball_local(self):
        """Smooth ball, centre at origin, hub toward -x. The M5 arm screws into a
        heat-set insert; the cord passes down through the ball and is knotted
        in a pocket underneath."""
        P = self.p
        R = P.ball_d / 2
        zl = P.arm_z - P.ball_z                                 # arm height in ball frame
        s = Solid.makeSphere(R, O, Z, -90, 90, 360)
        cuts = [
            cyl_x(P.arm_d + 0.3, R, -R - 1, 0, zl),             # rod clearance
            cyl_x(P.m5_insert_d, P.m5_insert_l, -3 - P.m5_insert_l, 0, zl),
            cyl(2.4, 2 * R + 2, -R - 1),                        # cord hole, top to bottom
            cyl(6, 4.5, -R - 1),                                # knot pocket underneath
        ]
        return tidy(s.cut(*cuts))

    def ball(self):
        return self.ball_local().translate(Vector(self.p.arm_r, 0, self.p.ball_z))

    def bracket(self):
        P = self.p
        zf, wo = -P.pf_thick, self.wall_out
        h = zf - self.bp_bot
        yb = self.fl_half - 10
        s = fuse(
            box(wo, -self.fl_half, self.flange_bot, self.fl_half - wo, 2 * self.fl_half, self.fl_t),  # flange
            box(wo, -yb, self.bp_bot, self.wall_t, 2 * yb, h),                                        # back wall
            box(wo, -yb, self.bp_bot, 16 - wo, 2 * yb, self.bp_top - self.bp_bot),                    # bottom plate
            cyl(20, self.clamp_h + EPS, self.bp_bot - self.clamp_h),                                  # pole clamp
            box(self.wall_in - EPS, 29, self.bp_bot, -self.wall_in - 26 + EPS, 5, h),                 # ribs
            box(self.wall_in - EPS, -34, self.bp_bot, -self.wall_in - 26 + EPS, 5, h),
        )
        cuts = [
            # top bearing: pocket opens downward, lip holds the outer race only
            cyl(P.brg_od + P.brg_fit, P.brg_w + 1, self.flange_bot - 1),
            cyl(P.race_relief_d, 10, self.brg1_top - EPS),
            # bottom bearing: pocket opens upward, relief so only the outer race is supported
            cyl(P.brg_od + P.brg_fit, P.brg_w + 2, self.brg2_bot),
            cyl(P.race_relief_d, 1 + EPS, self.brg2_bot - 1),
            # fixed pole through the plate and clamp
            cyl(P.pole_od + 0.15, 100, self.bp_bot - self.clamp_h - 1),
        ]
        for a in (0, 90):   # clamp set-screw inserts
            cuts.append(rotz(cyl_x(P.insert_d, 20, 0, 0, self.bp_bot - self.clamp_h / 2), a))
        for x, y in ((-31, 38), (-31, -38), (34, 38), (34, -38)):   # #6 wood screws, countersunk
            cuts += [cyl(3.8, self.fl_t + 1, self.flange_bot - EPS, x, y),
                     cone(8, 3.8, 2.2, self.flange_bot - EPS, x, y)]
        # opto slots: 90 +/- (45 + 45/4)/2 deg (quadrature for 8 slots), +/- 8 deg adjust
        for a in (90 - 28.125, 90 + 28.125):
            cuts.append(arc_block(39 - 1.7, 39 + 1.7, a - 8, a + 8, self.flange_bot - 1, self.fl_t + 2))
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

    # -------------------------------------------------------------- bought parts / reference
    def rotating_tube(self):
        P = self.p
        return ring(P.tube_od, P.tube_id, self.tube_bot, self.tube_top - self.tube_bot)

    def shaft_collar(self):
        P = self.p
        return ring(P.collar_od, P.tube_od, self.collar_z0, P.collar_w)

    def arm_rod(self):
        P = self.p
        return cyl_x(P.arm_d, self.rod_len, P.tube_od / 2, 0, P.arm_z)

    def pole_tube(self):
        P = self.p
        return ring(P.pole_od, P.pole_id, self.pole_bot, self.pole_top - self.pole_bot)

    def playfield(self):
        P = self.p
        return box(-80, -80, -P.pf_thick, 160, 160, P.pf_thick).cut(
            cyl(P.pf_hole_d, P.pf_thick + 2, -P.pf_thick - 1))

    def bearings(self):
        P = self.p
        return {"bearing_top": ring(P.brg_od, P.tube_od, self.flange_bot, P.brg_w),
                "bearing_bottom": ring(P.brg_od, P.tube_od, self.brg2_bot, P.brg_w)}

    # -------------------------------------------------------------- the cord
    def cord_exit(self):
        return Vector(0, 0, self.p.pole_h)

    def cord_ball_end(self):
        P = self.p
        return Vector(P.arm_r, 0, P.ball_z + P.ball_d / 2)

    def cord_neutral(self):
        """Hanging straight from the pole top to the top of the ball."""
        return cyl_between(self.p.cord_d, self.cord_exit(), self.cord_ball_end())

    def cord_wrapped(self, direction=-1):
        """Wound turns_each_way times around the sleeve. direction=-1 is the hub
        turning clockwise (seen from above) from neutral, i.e. toward the upper
        stop. Coils start just under the dome and stack downward, then the
        cord leaves the pole tangentially for the ball."""
        P = self.p
        r = P.sleeve_d / 2 + P.cord_d / 2              # coil centre-line radius
        b = self.cord_ball_end()
        d = math.hypot(b.x, b.y)
        # tangent point on the coil circle, continuing the winding direction
        phi = math.degrees(math.atan2(b.y, b.x)) - direction * math.degrees(math.acos(r / d))
        coil_pitch = P.cord_d * 1.05
        z_top = P.pole_h - 3
        height = self.N * coil_pitch
        z_bot = z_top - height
        # helix from the bottom of the coil upward; a clockwise-down winding is a
        # right-hand helix going up (and the mirror image for direction=+1)
        path = Wire.makeHelix(coil_pitch, height, r, Vector(0, 0, z_bot), Z, lefthand=(direction > 0))
        path = path.rotate(O, Z, phi)
        start = path.startPoint()
        tangent = path.tangentAt(0)
        prof = cq.Workplane(cq.Plane(origin=start, xDir=Z.cross(tangent).normalized(), normal=tangent)) \
            .circle(P.cord_d / 2)
        coil = prof.sweep(cq.Workplane().add(path), isFrenet=True).val()
        top = path.endPoint()
        lead_in = cyl_between(P.cord_d, self.cord_exit(), top)          # over the dome into the first coil
        lead_out = cyl_between(P.cord_d, start, b)                     # off the pole to the ball
        return fuse(coil, lead_in, lead_out)


# ------------------------------------------------------------------ registry
PRINTED = ["lower_hub", "encoder_disc", "nut", "stop_collar", "bracket",
           "pole_sleeve", "tube_bushing", "ball"]
_RGB = {"red": (0.95, 0.38, 0.28), "gold": (0.95, 0.80, 0.10), "blue": (0.27, 0.51, 0.71),
        "light": (0.80, 0.80, 0.80), "white": (0.97, 0.97, 0.97), "pale": (0.68, 0.85, 0.90),
        "yellow": (0.98, 0.84, 0.25), "steel": (0.75, 0.75, 0.78), "dark": (0.40, 0.40, 0.42),
        "rope": (0.85, 0.75, 0.55)}
COLORS = {"lower_hub": "red", "stop_collar": "red", "encoder_disc": "gold", "nut": "blue",
          "bracket": "light", "pole_sleeve": "white", "tube_bushing": "pale", "ball": "yellow",
          "strikers": "steel", "pole_tube": "steel", "rotating_tube": "steel", "shaft_collar": "steel",
          "arm_rod": "dark", "bearing_top": "dark", "bearing_bottom": "dark", "cord": "rope"}


def color(name):
    return cq.Color(*_RGB[COLORS[name]])


def print_pose(m: Tetherball, name: str, s):
    """Move a world-positioned part into its recommended print orientation."""
    P = m.p
    t = lambda z: Vector(0, 0, z)
    if name == "lower_hub":    return s.rotate(O, X, 180).translate(t(m.lh_top))   # boss down, tooth up
    if name == "encoder_disc": return s.translate(t(-m.disc_bot))
    if name == "nut":          return s.translate(t(-m.nut_bot_up))
    if name == "stop_collar":  return s.translate(t(-(m.c_top - m.c_t - 1)))         # boss on the bed
    if name == "bracket":      return s.translate(Vector(-m.wall_out, 0, 0)).rotate(O, Y, -90)  # back wall down
    if name == "pole_sleeve":  return s.translate(t(-m.sleeve_bot))
    if name == "tube_bushing": return s.translate(t(-(m.tube_top - 8)))
    if name == "ball":         return m.ball_local().translate(t(P.ball_d / 2))     # as modelled, tree supports
    raise KeyError(name)


def neutral_pose(m: Tetherball, name: str, s):
    """Parts as assembled at neutral: rotating parts are at 0 mod 360, the nut is mid-travel."""
    if name in ("nut", "strikers"):
        return s.translate(Vector(0, 0, -m.N * 360 / m.k_lead))
    return s


def write_step(shape, path: Path) -> str:
    """Write a part as STEP and prove it re-imports as one valid solid of the
    same volume. OCCT's writer can mangle faces with many trimming loops when
    it writes pcurves (parameter-space curves). pcurves are optional in STEP and
    CAD importers rebuild them, so a part that fails is rewritten without them
    and checked again."""
    for opt in ({}, {"write_pcurves": False}):
        cq.exporters.export(shape, str(path), opt=opt)
        r = cq.importers.importStep(str(path)).val()
        if (len(r.Solids()) == 1 and r.isValid()
                and abs(r.Volume() - shape.Volume()) < 1e-3 * shape.Volume()):
            return "verified" + (", no pcurves" if opt else "")
    raise RuntimeError(f"{path.name} failed STEP round-trip: {len(r.Solids())} solids, "
                       f"valid={r.isValid()}, volume {r.Volume():.1f} vs {shape.Volume():.1f}")


def build_assembly(m: Tetherball, wrapped: bool):
    """Neutral: nut mid-travel, cord straight. Wrapped: nut at the upper stop,
    cord coiled turns_each_way times (rotating parts are in the same place)."""
    assy = cq.Assembly(name="tetherball_wrapped" if wrapped else "tetherball")
    nut_dz = 0 if wrapped else -m.N * 360 / m.k_lead
    for name in PRINTED:
        s = getattr(m, name)()
        if name == "nut":
            s = s.translate(Vector(0, 0, nut_dz))
        assy.add(s, name=name, color=color(name))
    for i, st in enumerate(m.strikers_at(m.nut_bot_up)):
        assy.add(st.translate(Vector(0, 0, nut_dz)), name=f"striker_{'top' if i == 0 else 'bottom'}",
                 color=color("strikers"))
    for name in ("rotating_tube", "shaft_collar", "arm_rod", "pole_tube"):
        assy.add(getattr(m, name)(), name=name, color=color(name))
    for name, s in m.bearings().items():
        assy.add(s, name=name, color=color(name))
    assy.add(m.cord_wrapped() if wrapped else m.cord_neutral(), name="cord", color=color("cord"))
    return assy


def export_assembly(m: Tetherball, wrapped: bool, path: Path):
    assy = build_assembly(m, wrapped)
    expected = len(list(assy.traverse())) - 1
    assy.export(str(path), write_pcurves=False)      # pcurves off: see write_step()
    back = cq.importers.importStep(str(path)).val().Solids()
    if len(back) != expected or not all(x.isValid() for x in back):
        raise RuntimeError(f"{path.name} round-trip: {len(back)} solids (expected {expected})")
    return len(back)


# ------------------------------------------------------------------ commands
def cmd_export(m: Tetherball):
    step_dir, stl_dir = HERE / "step", HERE / "stl"
    step_dir.mkdir(exist_ok=True)
    stl_dir.mkdir(exist_ok=True)
    for name in PRINTED:
        s = getattr(m, name)()
        how = write_step(neutral_pose(m, name, s), step_dir / f"{name}.step")
        cq.exporters.export(print_pose(m, name, s), str(stl_dir / f"{name}.stl"),
                            tolerance=0.02, angularTolerance=0.15)
        print(f"  {name:13s} -> step/{name}.step ({how}), stl/{name}.stl")
    for wrapped, fn in ((False, "tetherball_assembly.step"), (True, "tetherball_assembly_wrapped.step")):
        n = export_assembly(m, wrapped, step_dir / fn)
        print(f"  assembly      -> step/{fn} (verified, {n} solids)")


def cmd_check(m: Tetherball) -> int:
    """Interference tests: travelling-nut stop, plus clearances of everything that turns."""
    print("building parts...", flush=True)
    lh, sc = m.lower_hub(), m.stop_collar()
    nut, stk = m.nut(), m.strikers_at(m.nut_bot_up)
    moving_extra = [m.encoder_disc(), m.ball(), m.rotating_tube(), m.shaft_collar(),
                    m.arm_rod(), m.tube_bushing()]
    fixed = [m.bracket(), m.playfield(), m.pole_tube(), m.pole_sleeve()]
    every = [("lower_hub", lh), ("stop_collar", sc), ("nut", nut)] + \
        [(f"moving_{i}", x) for i, x in enumerate(moving_extra)] + [(f"fixed_{i}", x) for i, x in enumerate(fixed)]
    bad = [n for n, x in every if not x.isValid()]
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
                # solid for parts that are clearly apart, while the distance
                # query is reliable.
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

    def report(name, expect, v):
        nonlocal fails
        got = "hit" if v > 1e-3 else "clear"
        ok = got == expect
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'} {name:50s} expect {expect:5s} got {got:5s} ({v:.4f} mm^3)", flush=True)

    for name, a, wrong, expect in cases:
        rot, nuts = pose(a, wrong)
        report(name, expect, overlap(rot, nuts))
    for name, a in (("upper stop", 0), ("neutral", N * 360 + 45), ("lower stop", T)):
        rot, nuts = pose(a)
        movers = rot + nuts + [rotz(s, a) for s in moving_extra]
        report("turning parts vs bracket/playfield/pole at " + name, "clear", overlap(movers, fixed))
    # the cord must clear the ball/arm/collar except where it is tied on, and the sleeve except where it wraps
    report("neutral cord vs shaft collar and arm", "clear",
           overlap([m.cord_neutral()], [m.shaft_collar(), m.arm_rod()]))
    # the clearance test must be able to see a collision: shrink the playfield hole
    tight = Tetherball(replace(m.p, pf_hole_d=7))
    report("sanity: undersized playfield hole collides", "hit",
           overlap([m.rotating_tube()], [tight.playfield()]))
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
        print(f"  {k}: {v:.1f} mm" if "turns" not in k else f"  {k}: {v:g}")
    if a.command == "export":
        cmd_export(m)
    elif a.command == "check":
        sys.exit(cmd_check(m))


if __name__ == "__main__":
    main()
