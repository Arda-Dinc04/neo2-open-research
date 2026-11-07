# Read-only integration boundary

The orientation process owns its USB receive handle and parser. The video
process owns camera discovery, association, session, decoding and recording.
Integrate observations above those transports rather than making either
process claim the other's device interface or operate its session.

The first actual Mac video trial worked with the external USB host connection
removed and the transceiver still installed. USB-connected trials delivered no
video in the observed bench setup. Concurrent USB orientation plus Wi-Fi camera
preview is unverified; do not advertise that combination as working. Integration
may require a source-backed Wi-Fi attitude observation path or another validated
transport. The current read-only frame boundary remains independent of that
future transport choice.

Offline review subsequently found FC `03/43` (85-byte payloads), gimbal `04/05`
(50-byte payloads) and battery `03/55` (10-byte payloads) inside the saved camera
sessions' Wi-Fi forwarding envelopes. See [the route comparison](wifi-route-findings.md).
This is evidence for using the camera owner's received protocol data in a
future adapter without adding aircraft USB. The adapter and a live physical
check remain required; saved header/layout matches do not establish synchronized
pose or calibrated sensor values.

The separate camera worktree has since verified live browser WebRTC through a
local MediaMTX bridge: 1280 × 720 at about 30 fps during an operator-ended
100.563-second preview. It retains JPEG fallback and uses an English viewer.
The bridge and signaling stay on loopback, while the Mac still switches Wi-Fi
to the aircraft. This playback implementation does not implement the proposed
orientation-viewer adapter below or establish concurrent USB telemetry. See
[the video milestone evidence](video-goal.md).

## Orientation viewer contract

The local viewer consumes the server's state snapshot at `GET /api/state`.
It exposes source mode (`live`, `replay`, `demo`), connection/freshness state,
aircraft and gimbal angle fields, source addresses/command, and receipt age.
Missing data stays unavailable. Bench markers annotate local observations;
display zeroing never changes device settings or raw readings.

The present `video` state may report `not_connected`. A placeholder panel is
not a working camera feed. The video workstream may add a separate read-only
adapter after agreeing a concrete transport and validating its lifecycle.

## Proposed video adapter v1

This is an integration design, not a claim that these endpoints are currently
implemented. The first useful adapter can be a loopback frame stream plus a
metadata endpoint; alternatively the video worker can publish observations
through a shared in-process interface. Keep the representation explicit.

Each frame observation should carry:

```json
{
  "schema": "neo2.video-frame.v1",
  "mode": "live",
  "stream_id": "session-local opaque value",
  "frame_sequence": 123,
  "status": "streaming",
  "received_monotonic_ns": 0,
  "decoded_monotonic_ns": 0,
  "camera_timestamp": null,
  "camera_clock_verified": false,
  "width": 1920,
  "height": 1080,
  "encoding": "jpeg",
  "payload_reference": "adapter-defined local frame reference",
  "dropped_frames_total": 0
}
```

The numeric values above are synthetic schema examples, not an observed Neo 2
stream. Stream/frame identifiers must distinguish reconnect generations.
Declare whether the payload is an original encoded access unit, a decoded
image, or a preview conversion. Do not label a JPEG preview as the original
camera stream.

Use a bounded latest-frame queue. A disconnected producer must age out visibly
instead of replaying the last frame as live. Recording can have a separate
bounded queue and must report any loss rather than blocking live observation
indefinitely. Local metadata should include the producer's status and last
frame age even when no image is available.

## Clock and alignment limits

USB packet receipt and video packet/frame receipt are host observations.
Monotonic times are comparable only when the processes share the same host
clock/time origin, or a measured mapping is provided. A frame's camera
timestamp must remain absent/unverified until its clock semantics are known.

Do not attach an aircraft/gimbal reading to an image as an exposure-time pose
merely because it is the nearest host timestamp. Camera-to-body transform,
gimbal reference frame, interpolation, sensor delays and camera exposure time
are separate validation work. An initial side-by-side viewer should show
independent ages and timestamps, without claiming synchronized reconstruction.

## Ownership and allowed actions

No flight or firmware method belongs in the observation adapter. Browser
clients can request local display/recording actions only through explicit,
same-origin allowlisted endpoints. Protect any local annotation/recording
mutation with the server's request token. Do not expose arbitrary packet,
command, shell, file-path or URL execution through the API.

The default host is loopback. External publication of a stream is a separate
deployment/sharing decision. Credentials, camera media, raw sensor data and
device identifiers are not included in the public source bundle by default.
