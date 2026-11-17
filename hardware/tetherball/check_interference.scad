// Interference checks for the travelling-nut stop.  Run ./check.sh.
// Each case intersects rotating parts (hub angle `a`) with the nut
// moved to where the screw puts it (dz = -a/k_lead, or +a/k_lead for the
// deliberate wrong-direction sanity case).  `expect` is printed by check.sh.
include <tetherball.scad>
part = "none";
which = "mesh";   // overridden with -D
a  = 90;
wrong = false;

dz = (wrong ? 1 : -1) * a / k_lead;

module rot()  { rotate([0, 0, a]) { lower_hub(); stop_collar(); } }
module nutp() { translate([0, 0, dz]) { nut(); strikers_at(nut_bot_up); } }

if (which == "mesh") intersection() { rot(); nutp(); }
else intersection() {
    union() { rotate([0, 0, a]) { upper_hub(); lower_hub(); encoder_disc(); stop_collar(); ball(); } nutp(); }
    union() { bracket(); playfield(); ring(16, pole_od, c_top - washer_t - collar_w, collar_w); }
}

// bracket clearance case (which = "bracket"): moving parts at angle a vs the bracket,
// the stop collar shaft collar and the playfield
module playfield() difference() {
    translate([-80, -80, -pf_thick]) cube([160, 160, pf_thick]);
    translate([0, 0, -pf_thick - 1]) cylinder(d = pf_hole_d, h = pf_thick + 2);
}
