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

### Current result, 6 November 2026

The operator confirmed an aircraft restart with DJI Fly closed and USB host
disconnected. Mac-only startup produced 407 frames in the initial attempt.
A follow-up Mac-only session ran for **478.925 seconds (7:59)**, decoded
**13,855 preview frames**, and delivered **359,206,127 video bytes**. It ended
when the operator stopped it. The operator explicitly relaxed the exact
ten-minute target; no full 600-second pass is claimed. After ten seconds,
the maximum observed video-delivery gap was 257 ms. Decoder cleanup passed.

A separate earlier coordinator error classified discovery-beacon expiry as
fatal despite fresh video. The preview status layer now reports that narrow
case as a warning after service commit, retaining all stale-video, command
and send-readiness restrictions. The regression suite passed 266 checks;
another physical trial of the fix remains separate from the eight-minute run.

The isolated Mac camera workstream has received and displayed actual aircraft
video: 22,764,198 video bytes, 1,329 encoded preview frames, and a retained
960 × 540 JPEG verified against the operator's live-page screenshot. Raw media,
stream identity and host packet-receipt timestamps remain private. The external
USB cable's Mac end was unplugged; the transceiver stayed installed. Earlier
USB-connected trials delivered no video. Concurrent USB orientation and Wi-Fi
preview is therefore not an established integration path.

Video arrived before the Mac service switch and encoder-refresh send. This run
followed a phone DJI Fly preview, so it did not by itself establish independent
cold activation or isolate USB removal as the sole cause. The later restart
test above demonstrated Mac-only startup; no new activation command was added.

The operator subsequently confirmed stopping the stream at 47.672 seconds;
the app labeled termination `network_error`. This does not establish a spontaneous
dropout. Rejected stale packets were at or behind the delivered frontier, so a
forward receive-window overrun has not been demonstrated. All cleanup checks
passed. The operator also attributed the slow connection to DJI Fly remaining
connected. That first run was not a full 60-second stability test. The later
Mac-only startup and longer preview results are recorded above. Exact 600-second
completion, reconnect and timestamped recording are not established.

| Milestone | Acceptance evidence |
| --- | --- |
| Mac compatibility | Document replacements or adapters for Linux-specific discovery, association and camera-session code; dependency/runtime checks pass on the Mac. Preserve a reviewed camera-only message allowlist. |
| First live frame | Receive, reassemble and decode an actual frame from the current aircraft. Show source mode, receipt time, frame dimensions and stream identity. A fixture, saved clip or synthetic frame cannot satisfy this milestone. |
| Reliable preview | Run a visible local preview for a documented duration. Ten minutes was the initial target; the operator accepted the 7:59 follow-up as useful bench evidence. Bound queues; report received/displayed frame counts, drops, last-frame age and decode failures. Do not infer camera exposure latency from host receipt timestamps or general long-running reliability from one trial. |
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
