# Read-only integration boundary

The orientation process owns its USB receive handle and parser. The video
process owns camera discovery, association, session, decoding and recording.
Integrate observations above those transports rather than making either
process claim the other's device interface or operate its session.

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
