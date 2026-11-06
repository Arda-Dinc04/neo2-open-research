# First exploratory orientation bench cycle

On 6 November 2026 the operator completed all seven guide steps in live USB
mode, with a duplicate initial baseline. The latest starting baseline was used.
The aircraft was reported powered on with DEP1 installed. These are aggregate
observations from private local annotations, not a calibrated reference dataset.
Pitch and roll tilts were estimated by hand; nominal 15° labels describe the
requested action, not independently measured angles. No packet scale was changed.

All differences below use circular subtraction of recorded absolute angles
against the preceding settled baseline. Baseline-return markers have stored
deltas of zero because they establish a new baseline; those deltas alone cannot
evaluate return error.

| Physical action | Aircraft ΔA / ΔB / ΔC | Candidate interpretation | Gimbal angle changes |
| --- | --- | --- | --- |
| Clockwise yaw, nominal 90° viewed from above | −0.3 / −1.9 / +93.5° | C positive clockwise | SDK yaw +93.4°; other two 0.0° |
| Nose up, nominal 15° estimated | +21.8 / +3.1 / +7.6° | A positive nose-up | SDK yaw +8.1°; other two 0.0° |
| Right side down, nominal 15° estimated | +1.3 / +23.1 / −1.5° | B positive right-side-down | SDK yaw −0.4°; other two 0.0° |

The dominant fields are distinct and support candidate A=pitch, B=roll, C=yaw.
One cycle does not establish repeatability. Estimated tilts cannot establish
whether the observed 21.8° and 23.1° are accurate or indicate a scale error.

Return errors on the tested field were yaw +2.4°, pitch −0.1° and roll −0.3°,
each within the provisional 3° diagnostic target. However, the pitch return
changed yaw by +10.3°, and the final aircraft heading was +12.5° from the initial
baseline. Gimbal yaw changed +12.4° across the session. Physical repositioning
and drift were not distinguished. The pitch movement also changed C by +7.6°;
this is a reason to constrain heading during the next measured tilt test.

Gimbal pitch and roll medians stayed close to zero during body tilts. This is
consistent with stabilization or an external reference frame, but does not prove
joint angles, camera alignment, quaternion convention, or a frozen sensor.

The original 0.75-second window contained only 1–2 aircraft samples and 7–8
gimbal samples per marker. A single-sample zero spread cannot establish low
jitter. The recorder now uses two seconds and requires at least three samples
spanning at least one second per channel. The live viewer sent zero DJI
application-command bytes throughout this receive-only test.

## Next evidence

1. Use a marked heading line and independent 90° yaw / 15° tilt references.
   Record whether each angle is measured; keep cable slack and the gimbal free.
2. Repeat the complete guide three times. Hold each pose at least three seconds
   and baselines five seconds. Check spread and return errors each time.
3. Keep heading fixed for pitch and roll. Compare both signs in a later recorded
   manual test to check convention symmetry; the built-in guide covers positive
   actions only. Do not force a negative tilt that the bench cannot support.
4. Investigate gimbal reference frame using independent visual camera-axis
   observations after the video workstream produces actual frames. Matching
   receipt times alone is not exposure-time synchronization.

Calibration remains unverified. These findings do not authorize flight or imply
an aircraft command API. Session analysis is offline and performs no device I/O.
