# USB routing/session investigation — reviewed 6–7 November 2026

## Outcome

An offline audit of **2,065 CRC-valid RX frames** found no General `00/ff`
packet at any source, destination, or sequence, and no RX frame with query
sequence `8101` at any command/address. Therefore the unanswered query is not
explained by our strict `03 → 0a` response filter overlooking another observed
PC instance. No new hardware reads or application transmissions were made for
this stage; the lifetime experiment still contains one identity request.

This narrows the problem; it does not establish a required USB handshake.
The remaining leading explanations are command support on the chosen logical
host, host-to-device forwarding/session policy, or another unobserved routing
requirement. An idle RX stream proves a receive path, not application delivery
of host-originated requests.

## Address/instance evidence

The reviewed DUML header implementation encodes a host byte as
`type = byte & 0x1f`, `instance = byte >> 5`. It is important not to use the
different bit packing described by some informal sources.

| Wire address | Type.instance | Interpretation from legacy source enum |
| --- | --- | --- |
| `03` | `3.0` | Flight-controller logical host |
| `04` | `4.0` | Gimbal logical host |
| `0a` | `10.0` | PC instance 0 |
| `2a` | `10.1` | PC instance 1 |
| `8a` | `10.4` | PC instance 4 |
| `48` | `8.2` | Legacy air-side-processor host type, instance 2 |
| `92` | `18.4` | Legacy vision-processor host type, instance 4 |

These are logical routing addresses. They do not identify physical chips,
prove which host is inside the detachable transceiver, or establish that
every host accepts the same command set. Our query used PC `10.0` and FC
`3.0`, which are both present in the received `03/43` route. Other PC instances
are present but have not been tried as transmitting identities.
[Header packing and enum](https://github.com/o-gs/dji-firmware-tools/blob/master/comm_mkdupc.py).

## Source cross-checks

1. The pinned Neo 2 client includes a receive-only USB census tool. It documents
   interface 4 emitting DUML without a host request, and names the same five
   idle command pairs we captured: `04/05`, `03/ce`, `03/43`, `00/82`, `00/f1`.
   This supports treating those streams as an idle baseline rather than a
   successful session negotiation. Its tool also looks for `00/99` subscription
   traffic; our saved data contains none.
   [USB census source](https://github.com/smichea/dji-neo2-lan-client/blob/014e3ad0d3ee98fecba94dfa48fe512a217a155f/tools/capture_usb_duml.py).
2. The legacy dissector names `00/ff` as an identity/build-info query, but we
   found no Neo 2 FC-handler implementation or known-good USB request/response
   trace demonstrating support on host `3.0`. Its presence in a generic command
   table is not proof of support on every module/model.
   [General command definitions](https://github.com/o-gs/dji-firmware-tools/blob/master/comm_dissector/wireshark/dji-dumlv1-general.lua).
3. The Neo 2 client's registration/device-info, heartbeat, WLM host-control,
   and session code concern BLE/Wi-Fi/SWUDP paths. For example, its Wi-Fi
   `07/93` message reports a physical port and caller-owned host identity;
   `00/b7` asks aircraft host `8.1` for selected declared capabilities.
   Neither proves a USB prerequisite. We did not replay them, change PC identity,
   or request control authority.
   [Neo 2 message construction](https://github.com/smichea/dji-neo2-lan-client/blob/014e3ad0d3ee98fecba94dfa48fe512a217a155f/src/neo2_control/duml.py),
   [session source](https://github.com/smichea/dji-neo2-lan-client/blob/014e3ad0d3ee98fecba94dfa48fe512a217a155f/src/neo2_control/session.py).

All observed RX packets have encryption bits zero. No response-bit packets,
`51/01` forwarding envelopes, `00/99` subscription-agent packets, or `07/93`
Wi-Fi registration messages occur in these captures. This describes the
saved windows only; startup, other routes, and other sessions were not captured.

An additional [Neo 2 USB host-source review](external-usb-source-review.md)
corroborated interface 4 using the saved configuration string. A subclass-only
fallback is nonunique across interfaces 3–7. The source's parameter-get paths
also call Assistant Unlock; they are not a receive-only procedure for this
project. This new evidence does not establish `00/ff` support or a required
identity-query handshake. No new device request or configuration operation ran.

## Capture and query limitations

- The initial query response read reached its approximately 64 KiB budget
  before its time deadline. Its trailing partial frame was a `03/43` FC
  broadcast, not the queried `00/ff` identity response.
- The separate five-second receive-only follow-up decoded another 828 frames
  with no matching response. There is a gap between the two captures and an
  interface release/reclaim, so these are not a continuous full-bus record.
- The logs contain bytes delivered to our reader, not an independent physical
  USB bus trace. A successful bulk write does not prove application acceptance.
- A long stream or an ever-larger command sweep is not a substitute for
  evidence about the correct model-specific query/session path.

## Useful component access already available

Offline field inspection decoded all 84 captured `04/05` gimbal packets using
the reference's exact 50-byte layout. SDK-mapped angle fields and four float
fields are finite; quaternion norms are approximately
`0.999999957` to `1.000000082`. All 17 `03/43` packets fit the locally observed
85-byte FC OSD layout, permitting provisional attitude-field inspection.
These are sensible numeric checks, not independent calibration of physical
axes, units, gimbal/camera alignment, absolute heading, or flight readiness.
[Gimbal field source](https://github.com/smichea/dji-neo2-lan-client/blob/014e3ad0d3ee98fecba94dfa48fe512a217a155f/src/neo2_control/gimbal_telemetry.py).

The FC offsets and tentative scaling come from the same pinned client's
[FC OSD decoder](https://github.com/smichea/dji-neo2-lan-client/blob/014e3ad0d3ee98fecba94dfa48fe512a217a155f/src/neo2_control/telemetry.py).

No dedicated `03/55` battery packet is present in the captured idle streams.
Battery percentage is not fabricated from unrelated bytes. No obstacle
range, image frame, or transceiver-specific metric has been verified.

Next evidence needed: a model-specific handler/source or a known-good USB
device-info session trace including both directions. Before any new request,
determine target host, source instance, transport envelope, and any registration
requirements from that evidence. Meanwhile, receive-only sensor visualization
and controlled bench calibration can progress without the identity query.

Historical audit and component-observation records remain private. Public
[source provenance](routing-source-provenance.json) is retained here. Reproduce
with `diagnostics/audit_routes.py` and `diagnostics/inspect_components.py` using
your saved captures; both operate on files and have no device I/O.
