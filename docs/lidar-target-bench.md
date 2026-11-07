# Stationary target experiment

This experiment looks for received fields that repeatably respond to a
measured target position. **No Neo 2 LiDAR distance decoder, depth grid or point
cloud is verified yet.** The guide records operator references and time
windows, not sensor measurements.

## Transport and scope

Use the existing preview-only Mac camera owner with the aircraft USB host
connection disconnected. Its separately authorized BLE registration, camera
service selection, transport acknowledgments/keepalives and bounded startup
refresh remain active communication. The target annotation tool adds no
aircraft requests, subscriptions or sensor activation; it reads local camera
status and the owner's existing incoming-packet file. No flight, motor,
firmware, gimbal, photo or onboard recording command is added.

The target guide has no aircraft socket or camera-control endpoint. Its only
outgoing HTTP requests are GETs to the existing loopback camera page/status.
It never joins Wi-Fi or starts/stops that owner. Network association and
cleanup remain the responsibility of a separately operated coordinator or
the operator. A camera image is optional for this experiment.

## Start the local guide

Requirements: Python 3.11+, the existing camera server on the same Mac, and a
new private output directory. The camera owner must expose its preview-only
status and write RX records with `monotonic_ns` in its session `swudp.jsonl`.

```sh
python3 diagnostics/lidar_bench.py \
  --capture-root /path/to/camera-fork/private/macos/camera-sessions \
  --output /path/to/new-private-target-session \
  --port 8767
```

Open `http://127.0.0.1:8767/`. The page is English and needs no external fonts,
scripts or internet connection. For this checkout, `local-data/` is an ignored
location suitable for private annotations. Source archives exclude that tree.
Restarting the guide requires a new output directory and begins a new test.

Readiness requires an active, preview-only camera owner, its current session
generation, a regular capture file, and an RX timestamp no more than three
seconds old. Outgoing traffic or a recent file modification alone cannot pass.
A camera owner still in its `connecting` phase can produce valid received
traffic, so its application-ready flag and decoded video are not prerequisites.
Stopped/failed owners, changed generations and stale RX data remain rejected.

## Physical setup and sequence

Keep the aircraft level and stationary with motors idle, USB disconnected,
DJI Fly closed and the phone disconnected from the aircraft Wi-Fi. Use the
same large, matte, opaque board throughout. Measure its width and height and
enter them on the page. Keep the board upright and centered ahead, covering
the forward sensor's height. Keep the background, lighting, aircraft position
and board orientation unchanged, with hands/body outside the forward view.

Mark distances from the **front edge of the airframe** to the near face of the
board. This is a repeatable mechanical reference; the sensor's optical origin
and offset remain unverified. A board smaller than the sensor's total field
of view may cover only some directions. Record dimensions rather than assuming
the board fills the whole sensing region.

| Hold | Target position |
| --- | --- |
| 1 | Clear baseline: remove the board from the forward view |
| 2 | Centered at 1.0 m |
| 3 | Centered at 0.5 m |
| 4 | Centered at 2.0 m |
| 5 | Centered at 1.0 m |
| 6 | Centered at 2.0 m |
| 7 | Centered at 0.5 m |
| 8 | Centered at 1.0 m |
| 9 | Clear return baseline |

At each position, check the measurement confirmation and click **Record
5-second hold**. The tool first allows three seconds to settle, then marks a
five-second observation window. Keep the pose until the next position appears.
Repeated, mixed distances help distinguish a distance-dependent field from a
counter or a gradual time trend. A clear baseline is not an infinite distance
or a known background range.

The backend records independently of browser polling. It checks the same
session/file identity and fresh RX throughout each hold; an interruption
invalidates the window and does not advance the step. A session change requires
a new test. Keep the raw capture and `target-windows.private.json` together
privately. Window timestamps use the same Mac's monotonic clock as packet
receipt, not a verified sensor acquisition clock.

Once the sequence is saved, end the camera session through its existing owner
and restore the usual Wi-Fi. A coordinator may perform that cleanup when it
detects all nine valid windows. If restoration is unconfirmed, use the macOS
Wi-Fi menu to rejoin the usual network; do not infer recovery from a cached page.

## Interpretation gate

Analyze only accepted RX frames whose receipt times lie inside valid windows.
Retain source/receiver, command, flags, payload length, counts and raw bytes
privately. Compare changes both within a hold and between repeated distances.
Seek the applicable model-specific layout before assigning physical units or
claiming a range API. Do not turn every changing two-byte field into a distance.

Even repeatable correlation with a board does not identify LiDAR ownership:
the vision cameras can see the same board. Sensor identity, units, scale,
invalid-value semantics, geometry and independent repeat tests remain separate
evidence. If grounded sensors report no changing data, the result is
inconclusive; this experiment does not authorize flight or activation probes.

See [existing vision traffic findings](vision-route-structure.md) and
[manufacturer sensing evidence](hardware-photo-map.md). The present guide
does not render an obstacle map or point cloud.

## Preparation results, 7 November 2026

The first attempt verified aircraft Wi-Fi and received protocol traffic but
decoded no camera frames. The initial guide incorrectly required video; that
gate was removed and regression-tested with fresh RX and no image. A second
attempt retained 10,282 RX datagrams and encoded 619 camera frames over about
23.3 seconds before a network-identity guard error. The operator subsequently
confirmed changing Wi-Fi or disconnecting that attempt. It does not establish
a spontaneous link dropout.

No target holds were recorded in either attempt. The second capture contains
additional source-92 routes, including changing payloads, but has no associated
measured target action. The previously observed `03/ce` and `24/71` payloads
remained constant in that file. None is promoted to a distance reading.

Synthetic tests cover receive freshness without video/application readiness,
TX-only/stale files, stopped owners, session changes, interrupted holds and
private annotation permissions. They establish software behavior, not LiDAR
access or physical measurement accuracy.
