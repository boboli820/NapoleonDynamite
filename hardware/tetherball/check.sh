#!/bin/sh
# Verifies the screw/nut mesh and the end stops by CSG intersection.
# PASS = result matches expectation ("clear" = empty intersection).
cd "$(dirname "$0")"
N=$(grep -E '^turns_each_way' tetherball.scad | sed 's/[^0-9]*\([0-9]*\).*/\1/')
T=$((N * 720))
run() { # name angle wrong expect
  out=$(openscad --backend=manifold -o /tmp/tb_check.stl -D "a=$2" -D "wrong=$3" check_interference.scad 2>&1)
  if echo "$out" | grep -q "empty"; then got=clear; else got=hit; fi
  [ "$got" = "$4" ] && r=PASS || r=FAIL
  printf '%-4s %-55s expect %-5s got %s\n' "$r" "$1" "$4" "$got"
}
run "screw/nut mesh, mid-travel (a=90+N*360)"        $((90 + N*360)) false clear
run "screw/nut mesh, odd angle (a=1337)"             1337            false clear
run "sanity: nut moved the WRONG way must collide"   $((90 + N*360)) true  hit
run "upper stop: at contact (a=0)"                   0               false clear
run "upper stop: 3 deg past contact is blocked"      -3              false hit
run "one turn before upper stop: teeth pass (a=360)" 360             false clear
run "lower stop: at contact (a=$T)"                  $T              false clear
run "lower stop: 3 deg past contact is blocked"      $((T + 3))      false hit
run "one turn before lower stop: teeth pass"         $((T - 360))    false clear
runb() { # name angle
  out=$(openscad --backend=manifold -o /tmp/tb_check.stl -D 'which="bracket"' -D "a=$2" check_interference.scad 2>&1)
  if echo "$out" | grep -q "empty"; then r=PASS; got=clear; else r=FAIL; got=hit; fi
  printf '%-4s %-55s expect clear got %s\n' "$r" "$1" "$got"
}
runb "bracket/playfield clearance at upper stop"  0
runb "bracket/playfield clearance at neutral"     $((N * 360 + 45))
runb "bracket/playfield clearance at lower stop"  $T
