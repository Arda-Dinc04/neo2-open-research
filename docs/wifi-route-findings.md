# Aircraft Wi-Fi observations alongside video

On 7 November 2026, an offline audit inspected four previously recorded actual
aircraft camera sessions. It found aircraft attitude, gimbal and battery-message
routes while video was arriving with the aircraft USB host connection removed.
This is new analysis of saved traffic, with no new device I/O or commands.
Camera-session ownership stays with the separate video workstream.

The finding supports a future side-by-side video/attitude viewer using the
camera process's existing received protocol data. It does not establish a live
integration, physical calibration, exposure-time alignment or a Mac O4 bridge.

## Observed headers and lengths

All rows below are inner plaintext pushes, flags `00`, in exact `51/01`
forwarding envelopes with the source-supported 22-byte attribute trailer and
link category 2. Both outer and inner DUML CRCs are checked. Source/destination
values are logical addresses, not identified processors.

| Inner route | Command | Payload bytes | Observation |
| --- | --- | --- | --- |
| `03 → 0e`, also `03 → aa` | `03/43` | 85 | Same command and length used by the provisional FC attitude decoder; USB instead targeted `0a`. |
| `04 → 02` | `04/05` | 50 | Same command and length used by the provisional gimbal decoder; USB targeted `2a`. |
| `03 → 02` and `03 → 0e` | `03/55` | 10 | Separate battery push, absent from the earlier inspected USB idle windows. |
| `92 → 02` and `92 → 1c` | `03/ce` | 28 | Same logical sender, command and length as the USB vision-related candidate; meaning remains unknown. |
| `92 → 02` and `92 → 1c` | `24/71` | 7 | Additional source-92 traffic; sensor origin, fields and units remain unknown. |

The source-backed battery candidate places percentage at payload offset 8,
but this audit publishes header counts, not a calibrated battery API. Its
availability over Wi-Fi does not establish a USB subscription or query path.
The vision-related label for `92` comes from a legacy host enum; it still does
not assign a particular camera, LiDAR, sensor chip or DEP1 ownership.
Further [structural inspection](vision-route-structure.md) found constant
payloads and equal content sets at the two recipients; it did not establish a
sensor layout or physical units.

## Four independent saved windows

| Window | Session seconds | RX datagrams | FC `03 → 0e` occurrences | Gimbal `04 → 02` occurrences | Battery occurrences per destination |
| --- | --- | --- | --- | --- | --- |
| W1 | 27.229 | 1,787 | 215 | 210 | 15 |
| W2 | 47.672 | 18,854 | 469 | 470 | 47 |
| W3 | 100.699 | 56,249 | 1,001 | 1,000 | 100 |
| W4 | 478.925 | 275,176 | 4,744 | 4,744 | 479 |

Battery counts refer separately to each of `02` and `0e`. Multiple recipients
and possible repeated transport deliveries are not independent sensors or
unique measurement counts. Session duration includes startup and termination;
it is not the sampling interval of every listed route. These four windows are
not a continuous recording. Earlier operator-stopped sessions retain that
interpretation; an application `network_error` label is not proof of a dropout.

Across these windows, the audit processed 352,066 saved RX datagrams. All parsed
protocol aggregates were in type-1 status datagrams; video datagrams were
excluded. No complete `24/08` birdview-distance or General `00/ff` identity frame
was found within this method's scope. This is not proof those commands are
unsupported or unavailable in another state, nor a reason to probe variants.

A separate offline receipt-clock cross-check found FC, gimbal and battery
frames between the first and last video datagrams in each session. This
establishes receipt-time coexistence, not camera exposure synchronization.
The recorded session results all report feature flags `0f`, whose bit 0 selects
ACK mode 1 in the pinned session implementation. The auditor implements that
specific transport profile; it does not detect or support arbitrary ACK modes.

The [reviewed count summary](wifi-route-summary.json) excludes payloads, capture
hashes, session/network/device identifiers and user media. Original captures
and full private audit reports remain outside the repository.

## Reproduce offline

```sh
python3 diagnostics/audit_wifi_capture.py /path/to/private-swudp.jsonl --output /path/to/new-private-route-report.json
```

The tool uses only the Python standard library, opens a bounded regular saved
file, and writes a new report with mode 0600. It ignores existing annotations
and TX records, validates SWUDP lengths/checksum and complete DUML frames,
unwraps at most one exact plaintext forwarding envelope, and exports header
profiles. It has no sockets, USB access, session setup or application encoders.
Review reports before public sharing; the reproducibility digest belongs in
the private evidence record.

The census does not join split frames across datagrams, reconstruct reliable
receive windows, recover FEC or deduplicate packets. Coded protocol fragments
are explicitly skipped. Missing routes cannot be inferred from an incomplete
capture or from these limitations. Only complete contained frames contribute.

Wire structure and battery interpretation were checked against the pinned
upstream [transport](https://github.com/smichea/dji-neo2-lan-client/blob/014e3ad0d3ee98fecba94dfa48fe512a217a155f/src/neo2_control/transport.py),
[forwarding decoder](https://github.com/smichea/dji-neo2-lan-client/blob/014e3ad0d3ee98fecba94dfa48fe512a217a155f/src/neo2_control/wlm_discovery.py)
and [battery decoder](https://github.com/smichea/dji-neo2-lan-client/blob/014e3ad0d3ee98fecba94dfa48fe512a217a155f/src/neo2_control/battery.py).
Exact reviewed blob identifiers are in [source provenance](wifi-route-source-provenance.json).

## Next integration evidence

The camera owner can expose received attitude/gimbal observations above its
existing transport, retaining source route, layout, receipt time and independent
freshness. That avoids assigning its socket or the USB observer's handle to a
second owner. A new live bench trial must establish current reception and
orientation behavior with video. Total camera delay, physical reference frames
and camera/body alignment remain separate measurements. No control authority
follows from receiving these observations.
