# Main Neo 2 research goal

Progressively understand and document the Neo 2's observable component and
communication architecture: aircraft USB, logical routes, flight-controller
and gimbal observations, camera/media, battery, vision/proximity sensors,
processors, Wi-Fi/BLE, and installed DEP1/O4 hardware. Produce original open
host tools and reproducible findings while using stock firmware and keeping
the current work read-only.

This is an ongoing research objective. A component map containing explicit
unknowns is useful progress; it is not complete understanding. Do not claim
that a logical host address identifies a physical chip, that an open host tool
makes vendor firmware open source, or that receiving telemetry establishes a
programmable flight interface.

## Near-term outcomes

1. Deliver a working live receive-only aircraft/gimbal viewer with raw/source
   attribution, stale/disconnected handling, and replay/demo provenance.
2. Record controlled bench tests to establish axis order, sign and approximate
   scale for the fields actually tested; leave untested frames/axes provisional.
3. Refresh inventory for the current transceiver installation, then map any
   component-specific changes with powered-off physical comparisons and cited
   evidence. No module hot-swapping or powered disassembly.
4. Resolve the device-info request's support/routing/session question from a
   handler/source or known-good two-direction trace before a different request.
5. Maintain the [component matrix](components.md), evidence provenance,
   compatibility conditions, reproducible captures and open questions.
6. Integrate the separate camera workstream through the [observation contract](integration.md)
   after its first real Mac frame and reliable preview are demonstrated.

## Evidence standard

For each capability, retain model/version if known, installation/power state,
transport/endpoints, exact command or packet layout, source revision, original
private capture, decoder checks and an independent physical check where
applicable. Label findings observed, source-backed, bench-validated or unknown.
Do not fill missing fields with plausible constants or substitute replay for
live hardware evidence.

Publish original receive-only tools, documentation, reviewed aggregate results
and synthetic tests. Keep raw user captures/media, per-device identifiers,
credentials and firmware binaries out of the public bundle. Preserve applicable
upstream attribution/licenses when incorporating actual third-party code.

Current boundaries: no flight, motor, firmware, parameter-setting,
configuration-changing or undocumented probe commands. A future control
project requires separate authorization and validation; it is not a dependency
of the orientation, component-mapping or video milestones.

## Workstream ownership

| Chat | Owns |
| --- | --- |
| Main: Neo 2 research | USB discovery/routing, component/transceiver mapping, receive-only orientation tools, bench validation and protocol evidence |
| Neo 2 video viewer | Upstream camera fork, Mac compatibility, first real frame, preview reliability and recording |

Share data models and evidence, not ownership of the same transport handle.
Keep progress reports specific about what changed, what was tested and what
remains unknown. Mark milestones complete only when their stated evidence is
present; keep the broader component-understanding goal open as required work
remains.
