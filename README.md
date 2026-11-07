# neo2-open-research

Open receive-only USB tools and a live aircraft/gimbal orientation viewer for
DJI Neo 2. The local Mac viewer receives real USB traffic and sends **zero DJI
application-command bytes**. This is host-side research around stock hardware;
no flight SDK or replacement firmware is claimed.

## Project and saved work

This is the main [Neo 2 open research repository](https://github.com/Arda-Dinc04/neo2-open-research).
Source, synthetic tests, protocol evidence and reviewed bench findings are
versioned here. The [research goal](docs/research-goal.md) tracks component
understanding and reproducible observations, with unknowns kept explicit.

The long-term [OpenNeo build brief](docs/compact-openneo-build-brief.md) defines
an original, reproducible aircraft with a printable frame, documented purchased
electronics, wiring and open software. The first prototype must be Neo-like
in size. This is a separate design workstream; no validated BOM, printable
airframe or equivalent DJI feature set is available yet.

The separate [Mac camera research fork](https://github.com/Arda-Dinc04/dji-neo2-lan-client/tree/codex/macos-camera-preview)
preserves its upstream history and owns BLE/Wi-Fi camera setup and playback.
It demonstrated real aircraft WebRTC video at 1280 × 720 and about 30 fps, with
an English viewer, JPEG fallback and read-only playback diagnostics. Camera
setup performs separately authorized registration/service-selection writes;
it is not receive-only USB observation. Keep the aircraft USB host connection
disconnected for that preview; concurrent USB telemetry and video is unverified.

| Area | Current evidence |
| --- | --- |
| USB inventory and orientation viewer | Live receive/decode/display verified; repeated measured axis tests remain pending. |
| Component and protocol map | Observed routes and source-backed fields documented; physical ownership and several message layouts remain unknown. |
| Mac camera | Actual WebRTC frames verified in the separate fork; total camera delay and real radio reconnect recovery remain unmeasured. |
| DEP1/O4 ground link | Aircraft-side module identified; a usable Mac ground-side bridge is not established. |

Private captures, credentials, device identifiers and user camera media remain
outside the public repositories. [Contribution guidance](CONTRIBUTING.md)
describes useful evidence and how to reproduce the software checks.

## Run the viewer

Requirements: Python 3.11+, an existing C compiler, and libusb development files.
These were already installed on the tested Apple Silicon Mac. No driver, kernel
extension, firmware update, or Python dependency installation is needed.

```sh
python3 tools/build_helper.py
python3 run_viewer.py --mode live
```

Open **http://127.0.0.1:8765**. The server binds only to loopback. The aircraft
must be powered on with a supported USB configuration. Remove the gimbal cover
if fitted and keep motors idle. A powered-off USB device can enumerate without
streaming orientation.

If sandbox USB access fails, run the same command in a normal Mac Terminal.
Do not use sudo or install drivers as a default response. If USB disconnects
or the helper exits, retained values are marked stale/error; restart the viewer
after reconnecting. Ctrl-C stops the server/helper and releases the interface.

The native helper accepts only `--receive-only`, validates descriptors, and
reads literal bulk **IN 0x85 on interface 4**. It temporarily claims an unbound
interface. It has no bulk OUT, vendor-request, reset, driver-detach, configuration,
flight, or firmware command path. Standard descriptor reads are used for
identification. Reads consume endpoint data; this is not a bus sniffer.

For a separate cached descriptor inventory that does not claim interfaces:

```sh
python3 tools/build_helper.py --target usb_descriptors
python3 diagnostics/usb_inventory.py capture --output /path/to/new-inventory.json
```

See the [USB comparison workflow](docs/usb-comparison.md) for offline diffs,
physical-state labels and limitations. Inventory excludes serial/product strings
and temporary bus addresses; an unavailable observation is inconclusive.

On macOS, inspect the existing driver tree without opening USB interfaces:

```sh
python3 diagnostics/macos_usb_bindings.py --output /path/to/new-bindings.json
```

The observed RNDIS interfaces had no attached network service on the tested
Mac. See [driver-binding findings](docs/macos-driver-bindings.md); this does not
establish firmware-side network capabilities or a reason to install drivers.

## Instruments and bench annotations

One exploratory bench cycle supports aircraft A=pitch, B=roll, C=yaw, positive
for nose-up, right-side-down and clockwise rotation from above. The viewer
labels these as candidates; scale accuracy and repeatability remain unverified.
See the [first bench findings](docs/first-bench-findings.md). Gimbal pitch/roll/yaw
labels follow a source-reconstructed SDK order. Quaternion conventions, camera
alignment and absolute heading remain unverified.
Each channel has its own receipt age and stale indicator. Mac receipt time
is not a verified sensor timestamp.

`GET /api/routes` provides a [bounded live header census](docs/live-route-census.md)
with mode provenance, route counts and receipt ages, excluding payload values,
angle data and the application's session token. It uses the existing receive
pipeline and sends no requests to discover additional message types.

**Zero this view** changes only that browser's display. It does not change
raw readings, exported bench measurements, or the aircraft.

Follow the built-in guide or [bench walkthrough](docs/bench-tests.md): a
stationary baseline, manual clockwise 90-degree yaw, return, nose-up 15 degrees,
return, right-side-down 15 degrees, and finish. Hold steady for at least three
seconds before marking. Baselines should remain stationary for five seconds.
Never force the gimbal. Markers require fresh live data from both channels;
replay/demo cannot validate physical axes.

Record buttons save local annotations only: recent sample medians, spread,
angle deltas, source provenance and the operator's expected physical action.
Each channel must contribute at least three samples spanning at least one
second within the preceding two-second window. Large spread is recorded as
unstable, not silently accepted as calibration.
No axis is automatically certified. Export bench-session JSON from the page.
New records also retain up to 128 [same-packet gimbal Euler/quaternion pairs](docs/gimbal-paired-evidence.md)
per marker, with selected original field bytes, source metadata and receipt
offsets. Polling carries counts only; full exports and local files contain the
samples. These are raw evidence, not a verified quaternion convention.
By default local records live under `local-data/bench-sessions/`, excluded from
Git and release archives. Do not commit raw captures or local session records.

Analyze an exported session entirely offline:

```sh
python3 diagnostics/analyze_bench.py /path/to/bench-session.json --reference estimated --output /path/to/new-private-analysis.json
```

Use `--reference measured` only when an independent angle reference was used.
The analysis recomputes circular differences from recorded absolute values;
return-baseline markers reset their stored deltas and need this comparison.
No analysis changes packet scaling or automatically certifies calibration.

## Replay and demonstration

These modes are visibly labeled and cannot record physical bench markers:

```sh
python3 run_viewer.py --mode replay --capture /path/to/private-capture.json --port 8766
python3 run_viewer.py --mode demo --port 8766
```

Replay uses recorded transfer offsets or a described fallback pacing. Demo
uses synthetic orientation and never opens USB. Neither is live validation.

## Workstreams

- [Compact OpenNeo aircraft](docs/compact-openneo-build-brief.md): original
  mechanical/electrical design, component budgets and a reproducible build;
  Neo-like size is required from the first prototype.
- [Main research goal](docs/research-goal.md): USB, routes, components, transceiver
  mapping, protocol evidence and reproducible bench validation.
- [Mac video-chat goal](docs/video-goal.md): upstream fork compatibility, first
  actual frame, reliable preview and timestamped recording.
- [Integration contract](docs/integration.md): independent transport owners,
  attributed frames and ages; no false exposure-time synchronization.
- [Component evidence](docs/components.md), [routing findings](docs/usb_routing.md),
  [additional USB host-source review](docs/external-usb-source-review.md),
  [Wi-Fi route comparison](docs/wifi-route-findings.md),
  [source-92 structural findings](docs/vision-route-structure.md),
  [passive packet findings](docs/passive-packet-findings.md),
  [hardware photo map](docs/hardware-photo-map.md),
  [external teardown findings](docs/independent-teardown-findings.md), [roadmap](docs/roadmap.md),
  [offline GNSS status candidates](docs/gnss-status-findings.md),
  [media metadata and clock evidence](docs/media-metadata-findings.md),
  and [viewer validation](docs/viewer-validation.md).

The orientation page's camera panel is a placeholder; this process opens no
video transport. Actual Mac camera playback lives in the separate fork above.
DEP1/O4 has not been assigned a separate USB interface or logical host. Receiving
aircraft data through its connector does not establish a Mac O4-adapter API.
No additional radio purchase is needed for current USB observation milestones.

## Tests and publication

```sh
python3 -m unittest discover -s tests -v
python3 tools/package_release.py
```

Tests cover framing, split/corrupt data, modes, stale states, source provenance,
angle wrap, cached USB comparison and local HTTP annotations. HTTP tests bind an isolated loopback
server with synthetic state; tests do not operate hardware. Source releases
exclude session records, raw captures, native binaries and local identifiers.

Original code/documentation is [MIT licensed](LICENSE). See
[source notices](THIRD_PARTY_NOTICES.md) for upstream evidence and attribution.
