# Passive status and battery audit

On 6 November 2026, offline analysis rechecked the earlier 2,065 CRC-valid
received frames, including 243 aircraft `03/43` payloads of exactly 85 bytes.
These files include the receive portions of the one historical identity-query
experiment. This audit performs no device I/O or new requests, and does not
pretend those saved windows are one continuous sensor-clock recording.

## Rejected legacy battery mapping

The legacy [flight-control dissector](https://github.com/o-gs/dji-firmware-tools/blob/master/comm_dissector/wireshark/dji-dumlv1-flyc.lua)
labels OSD payload byte 40 battery remaining. The reviewed routine describes
50/55-byte layouts. Our observed Neo 2 payload is 85 bytes, and that byte has:

| Receive window | Aircraft samples | Minimum / maximum | Values above 100 |
| --- | --- | --- | --- |
| Original powered-on vendor observation | 17 | 9 / 244 | 9 |
| Receive-only follow-up | 98 | 4 / 254 | 58 |
| Historical query experiment's received data | 128 | 4 / 254 | 76 |
| Combined | 243 | 4 / 254 | 143 |

Those observations contradict treating the byte directly as a 0–100 battery
percentage. No replacement scale, counter meaning or alternative field is
invented. Some early attitude offsets matching across layouts does not establish
that every later field matches. Even an in-range value alone would not validate
a battery interpretation.

The pinned Neo 2 [battery decoder](https://github.com/smichea/dji-neo2-lan-client/blob/014e3ad0d3ee98fecba94dfa48fe512a217a155f/src/neo2_control/battery.py)
uses a separate `03/55` message and percentage at payload offset 8. No `03/55`
packet appears in these saved USB windows. Its Wi-Fi source/session context is
not evidence of availability over USB. Battery percentage remains unavailable;
no battery request or subscription was sent.

## Status candidates and frame policy

The same pinned [FC OSD source](https://github.com/smichea/dji-neo2-lan-client/blob/014e3ad0d3ee98fecba94dfa48fe512a217a155f/src/neo2_control/telemetry.py)
supports a mode code at byte 30 and a little-endian status word at byte 32.
Its motor-on mask is `0x08`; its flying pattern is `(flags & 0x0e) == 0x0c`.
All 243 inspected samples had code 6 and the motor-on bit clear. This is
consistent with the reported idle bench conditions, but verifies neither mode
6's meaning nor status behavior in other conditions. Offline inspection exports
these only as explicitly unverified SDK candidates; no action or health verdict
depends on them.

The viewer now accepts orientation only with the source-supported packet flags:
FC plaintext push modes `00`, `20`, `40`; gimbal mode `00`. CRC-valid responses,
unsupported flags and encrypted frames cannot refresh angle readings. Such
packets may still contribute to overall received-frame activity; each angle
channel retains its own freshness. Synthetic response tests prove this filter,
not physical aircraft status semantics. Source hashes are in
[packet provenance](packet-source-provenance.json) and
[routing provenance](routing-source-provenance.json).

## Reproduce

```sh
python3 diagnostics/inspect_components.py /path/to/capture.json --output /path/to/new-component-report.json
```

The report includes the legacy byte-40 range test and status candidates, while
excluding geographic position bytes. Keep full captures and local reports
private; publish reviewed aggregates. A known-good read-only USB battery trace,
model-specific layout evidence and independent battery indication are still
needed before promoting battery access. Do not replay Wi-Fi session setup or
probe command variants to compensate for the absent stream.
