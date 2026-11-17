# Tetherball toy: parametric model

A spinner toy in the style of the Stern truck spinner, changed to act like a
tetherball. The studded ball turns around a **fixed** pole, and a real cord
wraps around the pole as it turns. A traveling-nut stop under the playfield
ends the motion after `turns_each_way` turns in either direction, which is the
"wrapped" state. Hitting the ball from the other side unwinds it.

![assembly](assembly.png)

## Files

| File | What it is |
|---|---|
| `tetherball.scad` | The whole model. Change the parameters at the top (playfield thickness, turns, pitch, arm radius, pole height...). |
| `export.sh` | Writes every printable part to `stl/` in print orientation. Pass overrides through, e.g. `./export.sh -D pf_thick=12.7 -D turns_each_way=3`. |
| `check.sh` | Interference tests. Run it after changing any parameter. |
| `stl/` | Generated output (git-ignored). |

Needs OpenSCAD 2025+ (manifold backend): `brew install --cask openscad@snapshot`.

## What `check.sh` proves

* The nut follows the screw at any hub angle without colliding, and fails as
  expected when it is moved the wrong way (a sanity test).
* At both ends, a 3° overrun collides, so the stop really blocks.
* One turn before each stop, the stop teeth pass each other cleanly, so they
  can only engage on the final turn.
* Nothing that rotates touches the bracket, the shaft collar, or the playfield,
  at the upper stop, at neutral, and at the lower stop.

What it does **not** prove: print tolerances, strength under real pinball hits,
how much the cord drags, or whether the optos and switches fit. Check those on a
bench rig.

## Printed parts

| Part | Material | Orientation (as exported) | Notes |
|---|---|---|---|
| `upper_hub` | PETG / PA-CF | collar face down | 100% infill near the arm socket |
| `lower_hub` | PETG / PA-CF | socket face down | stop tooth faces up. Fine layers (≤0.16 mm) help the thread |
| `nut` | PETG / PA-CF | as exported | tab prints on the bed |
| `stop_collar` | PETG / PA-CF | tooth up | |
| `encoder_disc` | PETG, opaque (black) | flat | glue onto the lower hub's step, then line up the notch |
| `bracket` | PETG / PA-CF, 5+ walls | back wall on the bed | clamp boss needs a little support. A metal bracket is better long-term |
| `pole_sleeve` | any | as exported | the visible pole |
| `spacer`, `washer` | PETG | flat | an aluminium tube can replace the spacer |
| `ball` | PETG or TPU | arm socket down | needs tree supports. Or buy Stern's 515-2037-00 and drill it for the 5 mm rod |

## Hardware

* 2× 608 bearings (fidget-spinner bearings, 8×22×7)
* 8 mm OD stainless tube, ~6 mm ID, cut to the length `tetherball.scad` echoes (≈187 mm at defaults)
* 5 mm steel rod for the arm, length echoed (32 mm at defaults). File a flat for the set screw
* 1× 8 mm-bore shaft collar (≈16 OD × 9 wide)
* PTFE Bowden tube, 4 mm OD / 2 mm ID, run through the pole
* ~1.5 mm braided cord, plus a retractable ID-badge reel (light tension) below the pole
* M3 heat-set inserts: 3 in the upper tube, 3 in the lower hub, 2 in the nut, 1 for the arm set screw, 1 in the pole sleeve, 2 in the bracket clamp
* M3 SHCS: 3× M3×10 (lower hub to tube), 3× M3×8 (stop collar), **2× M3×6 used as strikers**
  (their heads are the nut's stop dogs, so Loctite them), set screws for the arm, sleeve, and clamp
* 4× #6 wood screws (bracket to playfield)
* 2× SS-5GL-type micro switches (M2) for **WRAPPED-CW / WRAPPED-CCW**
* 2× slotted optos for quadrature (see below)

## Assembly

1. Drill a 1-1/4" playfield hole. Press the top bearing into the `upper_hub`
   and drop the hub into the hole from above.
2. From below, slide the `spacer` up into the tube bore until it touches the
   top bearing's inner race.
3. Put the `encoder_disc` on the `lower_hub`. Fit the `lower_hub` onto the tube
   end and fix it with the 3 radial M3 screws. Press in the bottom bearing.
4. Thread the `nut` on from below, with both striker screws already fitted.
   Fit the `stop_collar` (its screw pattern only lines up one way).
5. Turn the nut to the middle of its travel: **neutral**, 4 turns from each stop.
6. Slide the `bracket` on from the front so the nut tab goes into the back-wall
   slot, and screw it to the playfield.
7. Insert the pole from the top through everything. Fit the `washer`, then the
   shaft collar under the bottom bearing, and push the collar up snug. Tighten
   the clamp set screws.
8. Put the `pole_sleeve` on top, pressing lightly on the top bearing's inner
   race, and tighten its set screw. The hub should spin freely without
   rocking. Sand the spacer if it binds.
9. Feed the cord through the PTFE liner. Knot it inside the ball (it threads
   down through the top hole), push in the arm rod, and clip the reel to the
   bottom end **with the hub at neutral**.
10. Fit the micro switches on the back face with the levers over the tab slot.
    Slide them in their slots so each one trips in the last ~½ turn.

## Encoder (quadrature)

The disc has 8 slots, 50% duty. The flange has two arc slots at 90° ± 28.125°
(56.25° apart = 1¼ slot pitches), so two optos hanging from them are a quarter
cycle out of phase. The slots allow ±8° of adjustment for fine-tuning. Opto
packages vary, so there is no hanger part yet. Tell me which opto you're using
and I'll add one.

## Changing it

* **More or fewer wraps:** `turns_each_way`. The thread and bracket lengthen automatically.
* **Different playfield:** `pf_thick` (default 3/4").
* **Under-glass height:** `pole_h` (default 70 mm). Measure your glass and ramps.
* **Stop tooth engagement:** `tooth_h`, `striker_h`, `pitch`. An assert stops
  you choosing teeth too tall for the pitch.
* At defaults the mechanism goes ≈106 mm below the playfield's underside
  (including the pole tail). Check for flipper or other mechs underneath.
