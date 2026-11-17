// =====================================================================
//  Tetherball pinball toy  -  parametric model
//  Units: mm.  World frame: z = 0 is the playfield TOP surface,
//  +x is the direction the arm points when the hub angle is 0.
//
//  Pick a part with `part` (or -D part="\"nut\"" on the command line).
//  "assembly" shows everything in place; the other values output a single
//  part already rotated into its recommended print orientation.
// =====================================================================

part = "assembly"; // [assembly, section, upper_hub, lower_hub, encoder_disc, nut, stop_collar, bracket, pole_sleeve, spacer, washer, ball]

// Hub angle for the assembly view, in degrees past the UPPER stop.
// 0 = wound fully one way, turns_each_way*360 = neutral,
// 2*turns_each_way*360 = wound fully the other way.
hub_angle = -1; // -1 means "neutral"

/* [Playfield] */
pf_thick   = 19.05;  // 3/4" playfield; change for yours
pf_hole_d  = 32;     // drill 1-1/4" (31.75 mm) for the upper hub tube

/* [Tetherball geometry] */
ball_d     = 32;     // studded ball diameter
ball_z     = 19;     // ball centre height above playfield (pinball centre is 13.5)
arm_r      = 50;     // pole axis -> ball centre
arm_d      = 5;      // steel rod for the arm
pole_h     = 70;     // top of pole above playfield (check glass/ramp clearance!)
sleeve_d   = 14;     // visible pole diameter (what the cord wraps on)

/* [Turn limit] */
turns_each_way = 4;  // turns from neutral to "wrapped", each direction
pitch      = 3;      // lead of the travelling-nut screw (mm per turn)
thread_r   = 20;     // screw major radius
thread_e   = 1.0;    // eccentricity of the screw profile (thread depth = 2e)
thread_clear = 0.35; // radial clearance nut <-> screw
nut_h      = 14;
tooth_h    = 2.0;    // printed stop teeth on hub ring and stop collar
tooth_w    = 30;     // printed tooth arc, degrees
striker_h  = 3.0;    // M3 socket-cap head height (strikers on the nut)
striker_d  = 5.5;    // M3 socket-cap head diameter
stop_c     = 0.6;    // running clearance for tooth tips
dog_r      = 23.5;   // radius of the stop teeth / strikers
big_d      = 52;     // OD of nut, hub ring, stop collar

/* [Encoder] */
slots      = 8;
disc_od    = 70;
disc_t     = 1.6;
slot_r0    = 29.5;
slot_r1    = 33.5;
opto_r     = 31.5;   // sensing radius (centre of slots)

/* [Hardware] */
brg_od     = 22;     // 608 bearing
brg_w      = 7;
brg_fit    = 0.15;   // added to pocket diameter
race_land  = 11.5;   // OD of anything that may touch the inner race only
outer_clear_d = 19.5;// ID of anything that must touch the outer race only
pole_od    = 8;      // stainless tube, ~6 mm ID
insert_d   = 4.0;    // M3 heat-set insert hole
insert_l   = 6;
m3_clear   = 3.4;
collar_w   = 9;      // off-the-shelf 8 mm shaft collar width
washer_t   = 1;

$fn = 96;
eps = 0.01;

// ---------------------------------------------------------------- derived
N         = turns_each_way;
theta_tot = 2 * N * 360;                         // hub rotation, stop to stop
k_lead    = 360 / pitch;                         // deg of hub rotation per mm of nut travel
g_stop    = max(striker_h, tooth_h) + stop_c;    // face-to-face gap at a stop
assert(tooth_h + striker_h + stop_c <= g_stop + pitch,
       "stop teeth too tall for this pitch: they would collide one turn early");
beta      = asin((striker_d / 2) / dog_r);       // half-angle subtended by a striker head

// upper hub (above playfield)
hub_bot   = 1.5;                  // collar clears the playfield by this much
hub_top   = 29.5;
hub_d     = 46;
tube_od   = 26;
hub_bore  = 13;
top_brg_z = hub_top - brg_w;      // underside of the top bearing

// lower hub (below playfield)
lh_top    = -pf_thick - 2;
socket_d  = 46;                   // OD of lower-hub socket section
socket_dp = 10;                   // how far the upper tube goes into it
tube_bot  = lh_top - socket_dp;
disc_bot  = lh_top - 14;
disc_top  = disc_bot + disc_t;
ring_t    = 3;
sh_z      = disc_bot - ring_t;    // underside of the stop ring = upper stop face

nut_top_up  = sh_z - g_stop;      // nut position at the UPPER stop
nut_bot_up  = nut_top_up - nut_h;
travel      = theta_tot / k_lead; // = 2 * N * pitch
nut_bot_low = nut_bot_up - travel;
c_top       = nut_bot_low - g_stop;        // lower-hub bottom = stop collar top
c_t         = 5;
thread_z0   = c_top;
thread_z1   = sh_z;

spacer_len  = top_brg_z - (c_top + brg_w) - 0.2;

// bracket
wall_in   = -39;
wall_t    = 5;
wall_out  = wall_in - wall_t;
fl_t      = 5;
bp_top    = c_top - washer_t - collar_w - 1.5;   // shaft collar hangs below the stop collar
bp_t      = 6;
bp_bot    = bp_top - bp_t;
clamp_h   = 14;
fl_half   = 44;

tab_w     = 5;
tab_h     = 5;
tab_end_x = wall_out - 6;
tab_z_up  = nut_bot_up + tab_h / 2;
tab_z_low = tab_z_up - travel;

pole_top  = pole_h - 8;
pole_bot  = bp_bot - clamp_h - 10;

rod_end_r = arm_r - 7;            // rod stops 7 mm short of the ball centre
rod_len   = rod_end_r - 11;

echo(str("=== TETHERBALL: pole tube length = ", pole_top - pole_bot, " mm (8 mm OD stainless tube)"));
echo(str("=== TETHERBALL: arm rod length   = ", rod_len, " mm (", arm_d, " mm steel rod)"));
echo(str("=== TETHERBALL: spacer length    = ", spacer_len, " mm"));
echo(str("=== TETHERBALL: depth below playfield underside = ", -(pole_bot) - pf_thick, " mm (incl. pole tail)"));
echo(str("=== TETHERBALL: nut travel = ", travel, " mm, stop-to-stop = ", theta_tot / 360, " turns"));

// ---------------------------------------------------------------- helpers
// Helical lobe screw. Profile = circle of radius (thread_r - e + add) offset by e.
// Its phase depends only on world z, so screw and nut always agree:
//   eccentric direction at height z = 360 * z / pitch  (right-hand).
// Slices are kept to <= 5 deg of twist each: coarser slices make the facets
// sag inward by more than the nut clearance and the parts bind.
module helix(z0, z1, add = 0, fn = 72) {
    L = z1 - z0;
    translate([0, 0, z0]) rotate([0, 0, 360 * z0 / pitch])
        linear_extrude(height = L, twist = -360 * L / pitch,
                       slices = ceil(L * 360 / pitch / 5), convexity = 6)
            translate([thread_e, 0]) circle(r = thread_r - thread_e + add, $fn = fn);
}

module arc_block(r0, r1, a0, a1, z0, h) {
    translate([0, 0, z0]) rotate([0, 0, a0])
        rotate_extrude(angle = a1 - a0, $fn = 192)
            translate([r0, 0]) square([r1 - r0, h]);
}

module ring(od, id, z0, h) {
    translate([0, 0, z0]) difference() {
        cylinder(d = od, h = h);
        translate([0, 0, -eps]) cylinder(d = id, h = h + 2 * eps);
    }
}

// angular pattern for the stop-collar screws: deliberately uneven so the
// collar (and its tooth) can only go on one way.
collar_screw_a = [0, 110, 230];
collar_screw_r = 14.5;
socket_screw_a = [30, 150, 270];

// ================================================================ PARTS
// All parts are modelled in WORLD position (hub angle 0, nut at upper stop).

module upper_hub() {
    difference() {
        union() {
            translate([0, 0, hub_bot]) cylinder(d = hub_d, h = hub_top - hub_bot);
            translate([0, 0, tube_bot]) cylinder(d = tube_od, h = hub_bot - tube_bot + eps);
        }
        // bore (clears the spacer)
        translate([0, 0, tube_bot - 1]) cylinder(d = hub_bore, h = 200);
        // top bearing pocket + outer-race-only shoulder relief
        translate([0, 0, top_brg_z]) cylinder(d = brg_od + brg_fit, h = brg_w + 1);
        translate([0, 0, top_brg_z - 1.5]) cylinder(d = outer_clear_d, h = 1.5 + eps);
        // arm socket (+x)
        translate([11, 0, ball_z]) rotate([0, 90, 0]) cylinder(d = arm_d + 0.15, h = 30, $fn = 32);
        // set screw onto the arm: insert from the top face
        translate([16.5, 0, ball_z]) cylinder(d = 3.2, h = 30, $fn = 24);
        translate([16.5, 0, hub_top - insert_l]) cylinder(d = insert_d, h = insert_l + 1, $fn = 24);
        // radial heat-set inserts in the tube end (lower hub screws in here)
        for (a = socket_screw_a)
            rotate([0, 0, a]) translate([tube_od / 2 - 5.5, 0, tube_bot + socket_dp / 2])
                rotate([0, 90, 0]) cylinder(d = insert_d, h = 10, $fn = 24);
    }
}

module lower_hub() {
    difference() {
        union() {
            // socket section (encoder disc slides over this)
            translate([0, 0, disc_bot - eps]) cylinder(d = socket_d, h = lh_top - disc_bot + eps);
            // stop ring
            translate([0, 0, sh_z]) cylinder(d = big_d, h = ring_t);
            // screw
            helix(thread_z0, thread_z1 + eps);
            // upper stop tooth (hangs below the ring)
            arc_block(dog_r - 2.5, big_d / 2, beta, beta + tooth_w, sh_z - tooth_h, tooth_h + eps);
        }
        // socket for the upper tube
        translate([0, 0, tube_bot]) cylinder(d = tube_od + 0.3, h = socket_dp + 1);
        // bore
        translate([0, 0, c_top - 1]) cylinder(d = hub_bore, h = 200);
        // bottom bearing pocket + relief
        translate([0, 0, c_top - 1]) cylinder(d = brg_od + brg_fit, h = brg_w + 1);
        translate([0, 0, c_top + brg_w - eps]) cylinder(d = outer_clear_d, h = 1.5);
        // radial screws into the upper tube (M3 x 10 SHCS), counterbored heads
        for (a = socket_screw_a) rotate([0, 0, a]) translate([0, 0, tube_bot + socket_dp / 2]) {
            rotate([0, 90, 0]) cylinder(d = m3_clear, h = 40, $fn = 24);
            translate([19, 0, 0]) rotate([0, 90, 0]) cylinder(d = 6, h = 10, $fn = 24);
        }
        // inserts for the stop collar
        for (a = collar_screw_a) rotate([0, 0, a]) translate([collar_screw_r, 0, c_top - 1])
            cylinder(d = insert_d, h = insert_l + 1, $fn = 24);
        // index mark for the encoder disc / arm direction (a notch at +x)
        translate([socket_d / 2, 0, lh_top - 4]) rotate([0, 0, 45]) cube([2, 2, 10], center = true);
    }
}

module encoder_disc() {
    difference() {
        ring(disc_od, socket_d + 0.3, disc_bot, disc_t);
        for (i = [0 : slots - 1])
            arc_block(slot_r0, slot_r1, i * 360 / slots, i * 360 / slots + 180 / slots,
                      disc_bot - 1, disc_t + 2);
    }
}

module nut_at(z_bot) {
    difference() {
        union() {
            translate([0, 0, z_bot]) cylinder(d = big_d, h = nut_h);
            // anti-rotation tab, rides in the bracket wall slot
            // (flush with the nut's bottom face so it prints on the bed)
            translate([tab_end_x, -tab_w / 2, z_bot])
                cube([-tab_end_x - big_d / 2 + 3, tab_w, tab_h]);
        }
        // internal thread, cut by the screw itself (same world phase)
        helix(z_bot - 1, z_bot + nut_h + 1, thread_clear);
        // inserts for the two striker screws (heads are the stop dogs)
        translate([dog_r, 0, z_bot + nut_h - insert_l]) cylinder(d = insert_d, h = insert_l + 1, $fn = 24);
        translate([dog_r, 0, z_bot - 1]) cylinder(d = insert_d, h = insert_l + 1, $fn = 24);
        // chamfer thread entries
        translate([0, 0, z_bot - eps]) cylinder(d1 = 2 * thread_r + 2, d2 = 2 * thread_r - 2, h = 2);
        translate([0, 0, z_bot + nut_h - 2 + eps]) cylinder(d1 = 2 * thread_r - 2, d2 = 2 * thread_r + 2, h = 2);
    }
}
module nut() { nut_at(nut_bot_up); }

// M3 socket-head strikers (for display / interference checks)
module strikers_at(z_bot) {
    color("silver") {
        translate([dog_r, 0, z_bot + nut_h]) cylinder(d = striker_d, h = striker_h, $fn = 32);
        translate([dog_r, 0, z_bot - striker_h]) cylinder(d = striker_d, h = striker_h, $fn = 32);
    }
}

// Lower stop collar. Its tooth meets the nut's lower striker after exactly
// theta_tot of hub rotation (a whole number of turns, so same hub-local angle).
collar_a0 = -beta - tooth_w;
module stop_collar() {
    difference() {
        union() {
            ring(big_d, outer_clear_d, c_top - c_t, c_t);
            arc_block(dog_r - 2.5, big_d / 2, collar_a0, collar_a0 + tooth_w, c_top - eps, tooth_h + eps);
        }
        for (a = collar_screw_a) rotate([0, 0, a]) translate([collar_screw_r, 0, c_top - c_t - 1]) {
            cylinder(d = m3_clear, h = c_t + 2, $fn = 24);
            cylinder(d = 6, h = 1 + 3, $fn = 24);
        }
    }
}

module spacer() { ring(race_land, pole_od + 0.3, c_top + brg_w + 0.1, spacer_len); }
module washer() { ring(race_land, pole_od + 0.3, c_top - washer_t, washer_t); }

module pole_sleeve() {
    base_d = 20; base_top = 40;
    difference() {
        union() {
            // inner-race-only foot
            translate([0, 0, hub_top]) cylinder(d = race_land, h = 1 + eps);
            translate([0, 0, hub_top + 1]) cylinder(d = base_d, h = base_top - hub_top - 1);
            translate([0, 0, base_top - eps]) cylinder(d1 = base_d, d2 = sleeve_d, h = 3);
            translate([0, 0, base_top]) cylinder(d = sleeve_d, h = pole_h - base_top - 2);
            // rounded top
            translate([0, 0, pole_h - 2]) cylinder(d1 = sleeve_d, d2 = sleeve_d - 4, h = 2);
        }
        // pole tube
        translate([0, 0, hub_top - 1]) cylinder(d = pole_od + 0.15, h = pole_top - hub_top + 1);
        // PTFE liner (4 mm OD) above the tube end
        translate([0, 0, pole_top - eps]) cylinder(d = 4.2, h = 5, $fn = 32);
        // flared cord exit (fairlead)
        translate([0, 0, pole_h - 3.5])
            rotate_extrude($fn = 64) difference() {
                square([4.5, 3.6]);
                translate([4.5, 0]) circle(r = 3.25, $fn = 48);
            }
        translate([0, 0, pole_h - 4]) cylinder(d = 2.6, h = 5, $fn = 32);
        // set screw (M3 insert) to clamp onto the pole
        translate([0, 0, hub_top + 6]) rotate([0, 90, 0]) cylinder(d = insert_d, h = 20, $fn = 24);
    }
}

module stud() {
    cylinder(d = 5, h = 2, $fn = 20);
    translate([0, 0, 2]) cylinder(d1 = 5, d2 = 3, h = 1.2, $fn = 20);
}

// Studded ball in its own frame (centre at origin, hub is toward -x).
module ball_local() {
    R = ball_d / 2;
    n = 40;
    golden = 180 * (3 - sqrt(5));
    difference() {
        union() {
            sphere(r = R, $fn = 64);
            for (i = [0 : n - 1]) {
                z = 1 - 2 * (i + 0.5) / n;
                lon = i * golden;
                lat = asin(z);
                // skip studs where the arm and the cord attach
                ok = !(z > 0.8) && !(cos(lat) * cos(lon) < -0.8);
                if (ok) rotate([0, 0, lon]) rotate([0, -lat, 0])
                    translate([R - 0.5, 0, 0]) rotate([0, 90, 0]) stud();
            }
        }
        // arm socket from the hub side; rod goes in 9 mm, knot sits beyond it
        translate([-R - 1, 0, 0]) rotate([0, 90, 0]) cylinder(d = arm_d + 0.15, h = R - 1, $fn = 32);
        // cord hole from the top down into the knot pocket
        translate([-4, 0, 0]) cylinder(d = 2.4, h = R + 1, $fn = 24);
        translate([-4, 0, 0]) sphere(d = 5.5, $fn = 24);
    }
}
module ball() { translate([arm_r, 0, ball_z]) ball_local(); }

module bracket() {
    z_fl = -pf_thick;
    difference() {
        union() {
            // flange against the underside of the playfield
            translate([wall_out, -fl_half, z_fl - fl_t]) cube([fl_half - wall_out, 2 * fl_half, fl_t]);
            // back wall
            translate([wall_out, -fl_half + 10, bp_bot]) cube([wall_t, 2 * fl_half - 20, z_fl - bp_bot]);
            // bottom plate
            translate([wall_out, -fl_half + 10, bp_bot]) cube([14 - wall_out, 2 * fl_half - 20, bp_t]);
            // pole clamp boss
            translate([0, 0, bp_bot - clamp_h]) cylinder(d = 20, h = clamp_h + eps);
            // side ribs
            for (s = [-1, 1]) translate([wall_in - eps, s > 0 ? 29 : -34, bp_bot])
                cube([wall_in * -1 - 26 + eps, 5, z_fl - bp_bot]);
        }
        // U-shaped opening for the hub (open toward +x so it slides on from the front)
        hull() {
            translate([0, 0, z_fl - fl_t - 1]) cylinder(d = big_d, h = fl_t + 2);
            translate([100, 0, z_fl - fl_t - 1]) cylinder(d = big_d, h = fl_t + 2);
        }
        // relieve the bottom plate around the stop collar / shaft collar
        // (plate top is already below them; just a pole hole here)
        translate([0, 0, bp_bot - clamp_h - 1]) cylinder(d = pole_od + 0.15, h = 100, $fn = 48);
        // clamp set screws (M3 inserts) from +x and +y
        for (a = [0, 90]) rotate([0, 0, a]) translate([0, 0, bp_bot - clamp_h / 2])
            rotate([0, 90, 0]) cylinder(d = insert_d, h = 20, $fn = 24);
        // #6 wood screws into the playfield underside (countersunk from below)
        for (p = [[-31, 38], [-31, -38], [34, 38], [34, -38]])
            translate([p[0], p[1], z_fl - fl_t - eps]) {
                cylinder(d = 3.8, h = fl_t + 1, $fn = 24);
                cylinder(d1 = 8, d2 = 3.8, h = 2.2, $fn = 24);
            }
        // opto mounting: tangential slots at 90 +/- (45 + 45/4) / 2 deg, +/- 8 deg adjust
        for (a = [90 - 28.125, 90 + 28.125])
            translate([0, 0, z_fl - fl_t - 1]) difference() {
                arc_block(39 - 1.7, 39 + 1.7, a - 8, a + 8, 0, fl_t + 2);
            }
        // slot for the nut tab
        translate([wall_out - 1, -tab_w / 2 - 0.5, tab_z_low - tab_h / 2 - 2])
            cube([wall_t + 2, tab_w + 1, travel + tab_h + 4]);
        // micro-switch mounting slots (M2), upper switch +y, lower switch -y.
        // Switch body lies along y against the back face, lever toward the tab.
        for (sw = [[tab_z_up + tab_h / 2 + 7, 1], [tab_z_low - tab_h / 2 - 7, -1]])
            for (yy = [sw[1] * 6, sw[1] * 15.5])
                hull() for (dz = [-4, 4])
                    translate([wall_out - 1, yy, sw[0] + dz]) rotate([0, 90, 0])
                        cylinder(d = 2.2, h = wall_t + 2, $fn = 16);
    }
}

// ================================================================ VIEWS
neutral   = N * 360;
ang       = hub_angle < 0 ? neutral : hub_angle;
nut_dz    = -ang / k_lead;

module rotating_parts() {
    color("tomato") upper_hub();
    color("tomato") lower_hub();
    color("gold") encoder_disc();
    color("tomato") stop_collar();
    color("dimgray") translate([11, 0, ball_z]) rotate([0, 90, 0]) cylinder(d = arm_d, h = rod_len, $fn = 24);
    color("orange") ball();
}

module assembly() {
    rotate([0, 0, ang]) rotating_parts();
    translate([0, 0, nut_dz]) { color("steelblue") nut(); strikers_at(nut_bot_up); }
    color("lightgray", 0.9) bracket();
    color("white") pole_sleeve();
    color("silver") translate([0, 0, pole_bot]) cylinder(d = pole_od, h = pole_top - pole_bot, $fn = 32);
    color("lightblue") spacer();
    color("lightblue") washer();
    color("silver") ring(16, pole_od, c_top - washer_t - collar_w, collar_w);
    // playfield slab (for reference)
    %difference() {
        translate([-80, -80, -pf_thick]) cube([160, 160, pf_thick]);
        translate([0, 0, -pf_thick - 1]) cylinder(d = pf_hole_d, h = pf_thick + 2);
    }
    // bearings (reference)
    %ring(brg_od, pole_od, top_brg_z, brg_w);
    %ring(brg_od, pole_od, c_top, brg_w);
}

// print orientations ----------------------------------------------------
if (part == "assembly") assembly();
else if (part == "section") difference() { assembly(); translate([-200, 0, -300]) cube([400, 200, 600]); }
else if (part == "upper_hub")    translate([0, 0, hub_top]) rotate([180, 0, 0]) upper_hub();     // collar face down
else if (part == "lower_hub")    translate([0, 0, lh_top]) rotate([180, 0, 0]) lower_hub();      // socket face down
else if (part == "encoder_disc") translate([0, 0, -disc_bot]) encoder_disc();
else if (part == "nut")          translate([0, 0, -nut_bot_up]) nut();
else if (part == "stop_collar")  translate([0, 0, -(c_top - c_t)]) stop_collar();
else if (part == "bracket")      rotate([0, -90, 0]) translate([-wall_out, 0, 0]) bracket(); // back wall on the bed
else if (part == "pole_sleeve")  translate([0, 0, -hub_top]) pole_sleeve();
else if (part == "spacer")       translate([0, 0, -(c_top + brg_w + 0.1)]) spacer();
else if (part == "washer")       translate([0, 0, -(c_top - washer_t)]) washer();
else if (part == "ball")         translate([0, 0, ball_d / 2]) rotate([0, -90, 0]) ball_local();                       // arm socket face down (use supports)
