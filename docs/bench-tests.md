# Read-only orientation bench tests

The viewer observes data. Its **Zero view** action changes the display
reference only; it does not calibrate, configure or command the aircraft.
Bench markers are local annotations. No flight, motor, firmware, gimbal-motion
or configuration commands are part of this procedure.

## Before starting

1. Put the aircraft on a clear, stable, nonconductive surface. Remove the
   gimbal protector if fitted. Leave space for the gimbal to stabilize.
2. Keep motors idle. Do not press takeoff/mode controls. Do not force or hold
   the gimbal mechanism. Support the aircraft body for the small manual tilts.
3. Use a USB cable with enough slack for the planned movement, without pulling
   the connector or dragging the aircraft. Stop if the cable or surface cannot
   support the test comfortably.
4. Record the transceiver installation state before the session. Do not remove
   or install it while powered. Follow DJI's installation instructions for any
   later installed-versus-removed comparison.
5. Confirm the viewer says **Live** and the aircraft/gimbal sample ages update.
   Replay and demo can test the UI but cannot validate physical axes. Missing,
   stale, or disconnected data is not a valid bench measurement.

USB timestamps are receipt times on the Mac, not verified sensor exposure or
sample times. Record the aircraft model/version if already available in a
device-information screen; do not update firmware for this test.

## Walkthrough

For each pose, settle for at least three seconds and place a local marker. Keep the
reference surface and the Mac fixed. Start with the aircraft's nose pointing
along a marked line. A paper right angle and a simple tilt reference are more
useful than guessing the motion from the 3D drawing.

The recorder uses a two-second window, requiring at least three samples per
channel spanning at least one second. A zero spread from a single sample cannot
establish stability. Inspect the recorded spread even when a marker succeeds.
New full exports retain a bounded subset of paired gimbal Euler/quaternion
fields from the same accepted packets, with receipt offsets and source metadata.
See [paired evidence and its limits](gimbal-paired-evidence.md). Older markers
without these samples cannot establish a quaternion convention retroactively.
The [first exploratory cycle](first-bench-findings.md) identified candidate
axes; repeat with measured references before evaluating scale accuracy.

| Step | Physical action | Marker / observation |
| --- | --- | --- |
| 1. Baseline | Leave the aircraft stationary and level for at least five seconds | Mark baseline. Note all three aircraft fields, gimbal fields, sample age and stationary variation. Then optionally zero the display. |
| 2. Yaw | Keeping the aircraft level, rotate the whole body clockwise **90° as seen from above** | Mark yaw +90. Identify the dominant aircraft field and its signed change; do not assume its label is already correct. |
| 3. Return | Rotate back to the marked starting direction and let it settle | Mark baseline return. Check repeatability and account for angle wrap. |
| 4. Pitch | Gently raise the whole aircraft's nose by about **15°**, using a reference if available | Mark nose up +15. Observe which aircraft field changes. Record gimbal behavior separately; stabilization may compensate. |
| 5. Return | Set it back on the level reference surface | Mark baseline return. |
| 6. Roll | Gently lower the whole body's right side by about **15°**, keeping the nose direction fixed | Mark right side down +15. Identify the dominant aircraft field/sign and observe the gimbal independently. |
| 7. Finish | Return to the initial pose, settle, and mark finish | Save the session and repeat each motion twice more if readings and handling are stable. |

For signs, describe the physical action first, then the measured positive or
negative change. A consistently negative reading during clockwise yaw can be
a valid coordinate convention; it is not automatically a sensor failure.
Do not change firmware or packet scaling to make the visual appear familiar.

Compute circular angle changes as `((current - baseline + 180) % 360) - 180`.
For example, crossing from 179° to -179° is a +2° change, not a -358° jump.
Use relative changes for yaw, not an assumption that the absolute heading is
geographic north. Keep raw values and the display reference separate.

## What a useful result looks like

These are initial bench acceptance targets, not DJI specifications or a flight
authorization. Tighten or revise them only with measured evidence:

- All interpreted samples have valid framing/checksums, recognized layouts,
  finite values and a fresh source age. Record gaps rather than interpolating
  them into apparently measured motion.
- A five-second stationary plateau has a small range; use **2° peak-to-peak**
  as an initial diagnostic threshold, and investigate larger variation before
  assigning axes. Passing this target alone does not establish accuracy.
- The same physical rotation produces the same dominant aircraft field and
  sign in three repetitions. Record all field deltas to expose cross-coupling.
- With a measured 90° yaw reference, a provisional **80–100°** response is a
  reasonable first scale check. With a measured 15° tilt, use **10–20°** as a
  first check. If the physical reference is only estimated, report the numeric
  result as exploratory and do not claim the scale passed a measured test.
- Returning to the reference pose should bring the corresponding aircraft
  angle within about **3°** of its earlier settled baseline. Investigate drift,
  reference movement, wrap handling and timing if it does not.

Do not apply those body-motion thresholds to the stabilized gimbal as if it
were rigidly attached. Gimbal angle order/sign, quaternion convention and
camera/body alignment require their own physical reference. Near-unit
quaternion norm is a structural check, not proof of correct axes or pose.

## Save a defensible result

Keep session mode, model/version if known, installation/power state, host
software revision, marker labels, physical reference accuracy, raw and display
angle deltas, sample ages, repetitions, and deviations. Publish a reviewed
aggregate or synthetic fixture; raw USB captures can contain identifiers and
location bytes. Mark only the axes actually tested as bench-validated.

Stop on unexpected motion, stalled data, or a handling problem. Power the
aircraft off between bench sessions. Saved-data analysis needs no powered
hardware. An unsuccessful test is a useful result when its conditions are
recorded.
