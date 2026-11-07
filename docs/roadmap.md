# Building an open Neo 2 research project

The practical goal is an open collection of protocols, original host tools,
component maps, reproducible observations, and eventually validated interfaces
around the stock aircraft. Replacing the flight controller firmware, camera
pipeline, and radio stack is a much larger, separate effort; none is currently
demonstrated. An open host tool does not make DJI's firmware or hardware designs
open source. Start with the useful access already proven.

## What can be built, in order

| Stage | Useful result | Evidence/gate | Extra hardware now |
| --- | --- | --- | --- |
| 1 | Open USB inventory, receive-only recorder, CRC decoder and routing census | Already working on this Mac; fixed capture format and tests | None |
| 2 | Aircraft/gimbal orientation viewer, timestamped motion logger, stream-rate and dropout diagnostics | Live receive/decode/display verified; one exploratory bench cycle supports candidate axes; repeated measured angle tests pending | None |
| 3 | Component capability map and reliable read-only device/battery/status API | Capture/source-backed target and session rules; no invented values or command sweeps | None initially |
| 4 | Photo/media integration and live camera research | Separate Mac fork demonstrated real WebRTC preview at 1280 × 720 and about 30 fps, plus an earlier operator-ended 7:59 preview; reviewed camera-only setup remains separate from USB observation | Existing Mac/aircraft worked; USB host disconnected; no total-delay or O4 ground-link claim |
| 5 | Obstacle/vision observations, radio diagnostics, additional sensors | Discover actual message layouts/endpoints first; hardware labels alone are insufficient | Defer purchases until a specific gap is known |
| Later | A bounded, validated control API | Separate authorization, simulation, explicit limits and demonstrated fail-safe behavior | Not in the current read-only scope |

## Your next bench session

1. Keep the current setup as the baseline: same Mac port/cable, transceiver
   installed, aircraft state recorded. Note the version shown in an existing
   device-info screen if available; do not update firmware for this investigation.
2. Make a short stationary, powered-on receive-only capture. Record the
   capture start and any operator actions. USB receipt time is not sensor time.
3. In a separately labeled capture, gently rotate the whole resting aircraft
   by known yaw increments, then do a small controlled tilt with motors idle.
   Do not force the gimbal mechanism. Compare which numeric fields move, their
   signs and scale, and the distinction between aircraft and stabilized gimbal.
   This would support a useful motion/pose viewer before any new command.
4. For the transceiver mapping experiment, use two separate powered-off
   setups: installed, and removed according to DJI's manual. Then collect
   equivalent inventory/idle captures through the appropriate aircraft port.
   No hot-swapping. This is an optional physical comparison, not an action
   performed in this investigation. Matching USB descriptors would not prove
   that the transceiver is unused; different behavior would be a lead to test.
5. Power the aircraft off between sessions. Software analysis of saved data
   does not require leaving it running.

## What the transceiver gives us

DJI identifies the detachable module as **DEP1 / O4**, while the aircraft also
has Wi-Fi and Bluetooth. DJI instructs installing it for compatible remote
controllers/goggles; the manual says its external USB-C port can also connect
the aircraft to a computer. That establishes a supported physical USB path,
not a documented generic radio-adapter API for the Mac.
[Official specifications](https://dl.djicdn.com/downloads/DJI_Neo_2/SG/20260112/DJI_Neo_2_Fly_More_Combo_Safety_Guidelines_v1.2.pdf),
[connection guidance](https://repair.dji.com/help/content?customId=01700043608&lang=en&paperDocType=ARTICLE&spaceId=17),
[manual](https://dl.djicdn.com/downloads/DJI_Neo_2/UM/20251210/DJI_Neo_2_User_Manual_v1.2_en.pdf).

Your installed unit is the aircraft-side endpoint of the supported O4 link.
For a Mac-to-aircraft O4 route, a compatible ground-side radio and a working
computer bridge would still need to be established. The unit you own has not
been demonstrated as a standalone Mac O4 dongle, and a second aircraft-side
module would not by itself establish the missing bridge. No compatible SDR
implementation was verified in the reviewed sources. There is no reason to
buy another radio/controller for the next USB telemetry milestones.

We have not assigned a physical USB interface or logical DUML host specifically
to DEP1. The installed-module comparison, hardware documentation, or a
component-specific known-good trace is needed to make that assignment.

## Open-source release plan

- Start a focused `neo2-open-research` repository: original receive-only code,
  protocol notes, supported-model/state matrix, synthetic tests, source links,
  and explicit verified/reported/unknown labels.
- The canonical source repository is [published on GitHub](https://github.com/Arda-Dinc04/neo2-open-research) with an MIT license for the
  original included tools. It intentionally contains no raw user captures,
  local device IDs, network inventory, firmware binaries, or active query tool.
- The separate [Mac camera fork](https://github.com/Arda-Dinc04/dji-neo2-lan-client/tree/codex/macos-camera-preview)
  preserves upstream attribution and history. Link the two workstreams through
  observations rather than sharing USB handles or camera-session ownership.
- Keep the full working capture bundle private. Its registry/product strings
  include per-device identifiers, and its raw frames may contain location data.
  Do not upload that ZIP as the public project. Export a reviewed aggregate
  result or purpose-made synthetic fixture instead; byte redaction would also
  require checksum recomputation and clear labeling as modified data.
- Credit upstream sources and preserve their licenses when incorporating their
  actual code. The prepared starter includes original implementations plus
  links/attribution; it does not redistribute vendor software or the reviewed
  GPL source files. A future contribution that copies code needs its applicable
  license handled in that contribution.
- Accept contributions with model/version, installed module, OS/backend,
  aircraft power state, exact reproducer, expected observation and limitations.
  Separate command encoders from transports; keep transmission disabled by
  default, even when later features are added.

Early contributions that would help most: known-good USB read-only session
traces, receive-only Windows/Linux confirmation, controlled angle-validation
datasets, and documentation of component identity/routing. A controller loan
or SDR purchase is unnecessary for publishing the first useful release.
