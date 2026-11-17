#!/bin/sh
# Exports every printable part to stl/ in print orientation.
# Pass overrides through, e.g.  ./export.sh -D pf_thick=12.7 -D turns_each_way=3
cd "$(dirname "$0")"; mkdir -p stl
for p in upper_hub lower_hub encoder_disc nut stop_collar bracket pole_sleeve spacer washer ball; do
  openscad --backend=manifold "$@" -D "part=\"$p\"" --export-format=binstl -o "stl/$p.stl" tetherball.scad 2>&1 | grep -E "ECHO|WARNING|ERROR" | grep -v "^$" | sort -u
  echo "  -> stl/$p.stl"
done
