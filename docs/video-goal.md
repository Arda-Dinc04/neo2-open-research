# Goal for the Neo 2 Mac video chat

> Adapt the upstream Neo 2 BLE/Wi-Fi camera path to macOS, demonstrate the
> first real frame from this aircraft, then deliver a reliable local preview
> and timestamped recording. Keep the camera path independent from the USB
> orientation observer and expose a documented read-only integration boundary
> for the open Neo stack. Use stock firmware. Send no flight, motor, firmware,
> calibration or unrelated configuration commands. Review camera-session setup
> messages before enabling them; do not invoke the upstream flight interface.

The upstream client targets Linux and uses BlueZ/NetworkManager-related
camera/session dependencies. A local fork is present, but copying it to a Mac
is not evidence of Mac compatibility or a live camera connection. The existing
source contains experimental flight functions that are outside this goal.

## Milestones and acceptance

| Milestone | Acceptance evidence |
| --- | --- |
| Mac compatibility | Document replacements or adapters for Linux-specific discovery, association and camera-session code; dependency/runtime checks pass on the Mac. Preserve a reviewed camera-only message allowlist. |
| First live frame | Receive, reassemble and decode an actual frame from the current aircraft. Show source mode, receipt time, frame dimensions and stream identity. A fixture, saved clip or synthetic frame cannot satisfy this milestone. |
| Reliable preview | Run a visible local preview for a documented test duration, initially 10 minutes. Bound queues; report received/displayed frame counts, drops, last-frame age and decode failures. Do not infer camera exposure latency from host receipt timestamps. |
| Disconnect/reconnect | Loss of packets becomes visibly stale/disconnected. Reconnect or provide a clear restart procedure; no old image is silently presented as current. Record the observed recovery time and resource cleanup. |
| Recording | Save the received elementary stream where available and/or the decoded recording, with explicit format and provenance. Record timestamps, frame counts, drops, source mode and recording start/stop events in a sidecar. Verify the saved file plays and covers the reported interval. |
| Open-stack integration | Implement the agreed [read-only frame contract](integration.md), with camera lifecycle owned by the video process. No second reader claims the orientation observer's USB interface. |

Use loopback-only local services by default. Mark preview, replay, demo and
recording modes explicitly. Credential/identity material and raw user media
remain private; a public release should contain original changes, source
attribution, synthetic fixtures and reproducible instructions.

## Responsibility split

- **Main research chat:** USB discovery/routing, component identity, protocol
  evidence, transceiver mapping and bench-validated orientation fields.
- **Video chat:** upstream fork, Mac BLE/Wi-Fi compatibility, first real frame,
  preview reliability, decoder/recording lifecycle and camera metadata.
- **Shared contract:** timestamped, attributed read-only observations. Neither
  workstream treats decode success as control authority or flight readiness.

No controller or additional radio purchase is assumed. If the current camera
transport cannot meet a milestone, report the exact missing capability and
evidence before changing the hardware plan.

References: [upstream protocol scope](https://github.com/smichea/dji-neo2-lan-client/blob/014e3ad0d3ee98fecba94dfa48fe512a217a155f/docs/PROTOCOL.md),
[upstream limitations](https://github.com/smichea/dji-neo2-lan-client/blob/014e3ad0d3ee98fecba94dfa48fe512a217a155f/docs/VALIDATION.md).
