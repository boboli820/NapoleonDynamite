# Tetherball toy: parametric model

A pinball toy that acts like a tetherball. A thin pole that never turns stands
on the playfield. A real cord comes out of its top and is tied to a smooth ball.
Hit the ball and it circles the pole, winding the cord around it. After
`turns_each_way` turns (4 by default) a stop under the playfield ends the
motion: that's "wrapped". Hitting the ball from the other side unwinds it and
winds it up the other way.

| Neutral (cord straight) | Wrapped (4 turns) |
|---|---|
| ![neutral](assembly.png) | ![wrapped](assembly_wrapped.png) |

## How it works

* **The ball is carried by a low steel arm, not the cord.** An M5 threaded rod
  screws into a steel 8 mm shaft collar at the base of the pole and into a
  heat-set insert in the ball. Pinball hits go through steel to the bearings.
  The arm meets the ball below its centre, so from above the cord looks like the
  thing holding the ball.
* **The pole stays still while a tube turns around it.** The visible pole is a
  printed 9.5 mm sleeve glued onto a 5 × 3 mm tube, clamped at the bottom of the
  bracket. Around it, an 8 × 6 mm tube passes through a 10 mm playfield hole and
  turns in two 608 (fidget-spinner) bearings, both under the playfield. The shaft
  collar and arm are fixed to the top of that tube.
* **The cord.** It runs down through the hollow pole to a retractable ID-badge
  reel under the bracket, comes out of a rounded exit in the pole cap, and is
  knotted under the ball after passing down through it. As the ball circles,
  the cord catches on the pole just under the cap and coils downward. Each turn
  pulls about 35 mm of cord out of the pole, so 4 turns pull about 140 mm. The
  reel takes the slack back in as it unwinds.
* **Turn limit, encoder and "wrapped" switches (all under the playfield).** A
  printed hub clamped to the turning tube carries a coarse screw. A nut on it
  can't rotate (its tab rides in a slot in the bracket wall), so it moves up or
  down 3 mm per turn. At ±4 turns, the M3 screw heads on the nut hit stop teeth
  on the hub, which is a hard stop. Micro-switches on the bracket wall detect
  each end. A slotted disc read by two optos gives turn count and direction.

## Files

| File | What it is |
|---|---|
| `step/<part>.step` | One STEP file per printed part: true solids (cylinders, planes, cones, a torus, an exact helical thread), not meshes. Each sits where it goes in the assembly, so importing them all lines them up. |
| `step/tetherball_assembly.step` | Everything at neutral, coloured, including bought parts and the cord. |
| `step/tetherball_assembly_wrapped.step` | The same, wound fully one way, with the cord coiled 4 times around the pole. |
| `tetherball.py` | The source model, in [CadQuery](https://cadquery.readthedocs.io). All parameters are in the `Params` class at the top. |
| `stl/` | Print-ready meshes in print orientation (generated, git-ignored). |

### Regenerating

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt   # once
.venv/bin/python tetherball.py export                                   # step/ + stl/
.venv/bin/python tetherball.py check                                    # interference tests (~1 min)
.venv/bin/python tetherball.py info --set pf_thick=12.7 --set turns_each_way=3
```

`--set name=value` overrides any parameter for `export`, `check` and `info`.
`info` prints the cut lengths for the tubes, the arm and the cord. `export`
re-imports every STEP file it writes and fails unless the file comes back as
one valid solid with the same volume.

## What `check` proves

* The nut follows the screw at any hub angle without colliding, and collides
  when it is moved the wrong way (a sanity test).
* At both ends, a 3° overrun collides, so the stop really blocks.
* One turn before each stop, the stop teeth pass each other cleanly, so they
  only engage on the final turn.
* Nothing that turns (tube, collar, arm, ball, hub, disc, nut) touches the
  bracket, the playfield, the fixed pole or the sleeve, at either stop or at
  neutral.
* The cord clears the collar and the arm.

What it does **not** prove: print tolerances, strength under real pinball hits,
how much drag the cord adds, or whether the optos and switches fit. Check those
on a bench rig.

## Printed parts

| Part | Material | Orientation (as exported) | Notes |
|---|---|---|---|
| `ball` | PETG (or TPU for a softer hit) | cord hole vertical | tree supports. Heat-set an M5 insert into the side socket |
| `pole_sleeve` | PETG, any colour | standing up | the visible pole; glue it onto the pole tube |
| `tube_bushing` | PETG | standing up | press into the top of the turning tube; steadies the pole |
| `lower_hub` | PETG / PA-CF | upside down (stop tooth up) | fine layers (≤0.16 mm) help the screw |
| `nut` | PETG / PA-CF | as exported | tab prints on the bed |
| `stop_collar` | PETG / PA-CF | bearing boss down | |
| `encoder_disc` | PETG, opaque (black) | flat | glue onto the hub's step, then line up the notch |
| `bracket` | PETG / PA-CF, 5+ walls | back wall on the bed | the clamp boss needs a little support. A metal bracket is better long-term |

## Hardware

* 2× 608 bearings (fidget-spinner bearings, 8×22×7)
* **Turning tube:** 8 mm OD × 6 mm ID stainless, ≈116 mm (`info`). File three
  small flats: one 4.5 mm from the top for the shaft collar, and two at 0° and
  270°, 49 mm from the top, for the hub set screws.
* **Fixed pole:** 5 mm OD × 3 mm ID stainless or brass tube, ≈197 mm (`info`)
* **Shaft collar:** 8 mm bore, about 16 mm OD × 9 mm wide. Drill and tap one
  M5 hole through its side for the arm (opposite its own set screw)
* **Arm:** M5 stainless threaded rod, 43 mm (`info`). Screw it through the
  collar until it bears on the tube (Loctite 243), and into the ball's insert
* 1× M5 heat-set insert (ball)
* ~1.5 mm braided cord, about 400 mm, plus a retractable ID-badge reel (light tension)
* M3 heat-set inserts: 2 in the lower hub, 3 in its bottom face, 2 in the nut,
  2 in the bracket clamp
* M3 × 20 set screws ×2 (lower hub onto the tube flats), M3 × 8 SHCS ×3 (stop
  collar), **M3 × 6 SHCS ×2 used as strikers** (their heads are the nut's stop
  dogs, so Loctite them), M3 set screws ×2 (pole clamp)
* 4× #6 × 3/4" wood screws (bracket to the playfield)
* 2× SS-5GL-type micro switches (M2) for **WRAPPED-CW / WRAPPED-CCW**
* 2× slotted optos for quadrature (see below)

## Assembly

1. Drill a 10 mm (or 3/8" plus a light ream) hole in the playfield. Press the
   bearings into the bracket: the top one from below into the flange, the
   bottom one from above into the bottom plate. Screw the bracket under the
   playfield, centred on the hole.
2. Fit the strikers to the `nut` and the `encoder_disc` to the `lower_hub`.
   Thread the nut onto the hub to the middle of its travel (**neutral**, 4 turns
   from each stop), then screw on the `stop_collar` (it only fits one way).
3. Slide that assembly into the bracket from the front, with the nut tab in the
   back-wall slot.
4. Push the turning tube down from above, through the playfield, top bearing,
   hub and bottom bearing. Turn it so the hub flats face the set screws, then
   tighten them. The hub should sit on the bottom bearing and spin freely.
5. Press the `tube_bushing` into the tube top. Put the shaft collar on the tube
   at the top flat, screw in the arm, and screw the ball onto the arm.
6. Slide the pole tube down through the bushing into the clamp and tighten the
   clamp screws. Glue the `pole_sleeve` onto it, leaving a small gap above the
   collar.
7. **Cord:** with the hub at neutral, feed the cord down through the cap and the
   pole, clip it to the reel underneath, then thread the other end down through
   the ball and knot it in the pocket underneath.
8. Fit the micro switches on the back face of the wall, levers over the tab
   slot. Slide them in their slots so each one trips in the last ~½ turn.

## Encoder (quadrature)

The disc has 8 slots at 50% duty. The flange has two arc slots at 90° ± 28.125°
(56.25° apart, or 1¼ slot pitches), so two optos hung from them read a quarter
cycle out of phase. Each slot allows ±8° of adjustment. Opto packages vary, so
there's no hanger part yet. Tell me which opto you're using and I'll add one.

## Changing it

* **More or fewer wraps:** `turns_each_way`. The screw and bracket lengthen automatically.
* **Different playfield:** `pf_thick` (default 3/4").
* **Under-glass height:** `pole_h` (default 70 mm). Measure your glass and ramps.
* **Look:** `sleeve_d`, `ball_d`, `arm_r`, `cord_d`. The checks will tell you if something collides.
* At defaults the mechanism goes ≈112 mm below the playfield's underside
  (including the pole tail). Check for flipper or other mechs underneath.
