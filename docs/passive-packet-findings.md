# Passive component traffic findings

On 6 November 2026, offline profiling inspected 971 CRC-valid frames from two
saved powered-on receive windows: 143 frames and 828 frames. These are a subset
of the earlier 2,065-frame routing audit; the historical request/response file
was not included here. Both windows used interface 4 IN `0x85`. Capture
boundaries were preserved, including four silent interface observations in
the first file. No hardware I/O or new device requests were performed.

| Route | Command | Payload bytes | First / second window frames | Within-window payload variation |
| --- | --- | --- | --- | --- |
| `03 → 0a` | `03/43` | 85 | 17 / 98 | Variable; recognized aircraft OSD layout |
| `04 → 2a` | `04/05` | 50 | 84 / 487 | Variable; recognized gimbal layout |
| `92 → 2a` | `03/ce` | 28 | 17 / 97 | One distinct payload in each window |
| `48 → 2a` | `00/82` | 64 | 9 / 48 | One distinct payload in each window |
| `04 → 2a` | `00/f1` | 8 | 8 / 49 | One distinct payload in each window |
| `04 → 8a` | `00/f1` | 8 | 8 / 49 | One distinct payload in each window |

The two `00/f1` receiver routes had equal payload sets within each window.
This supports logical fan-out of the same observed content; packet pairing,
delivery timing, physical processor ownership and subscriber identity are not
established. Neither file contained discarded bytes or trailing partial frames.

## What the legacy source does and does not establish

The [General dissector](https://github.com/o-gs/dji-firmware-tools/blob/master/comm_dissector/wireshark/dji-dumlv1-general.lua)
labels `00/f1` component self-test state. It reads an initial four-byte state
word; its radio-specific bit labels apply only to sender `09`. Our sender is
`04` and payload is eight bytes, so importing those radio meanings would be
unsupported. No health verdict is assigned from this message.

The [flight-control command table](https://github.com/o-gs/dji-firmware-tools/blob/master/comm_dissector/wireshark/dji-dumlv1-flyc.lua)
labels `03/ce` forbid-data information, without a corresponding handler in the
reviewed file. That legacy name does not establish the Neo 2 payload layout.
In particular, sender `92`'s legacy vision-host label does not establish that
the 28 bytes are obstacle distances. No distance or LiDAR output is claimed.
Content hashes are recorded in [source provenance](packet-source-provenance.json).

## Reproduce and extend

```sh
python3 diagnostics/profile_traffic.py /path/to/first-capture.json /path/to/second-capture.json --output /path/to/new-profiles.json
```

This offline tool accepts the saved-capture formats already used by the routing
audit. It groups by interface, sender, receiver, command, flags and payload
length, keeping each observation separate. Output includes frame counts,
distinct payload counts, changed byte offsets and per-byte cardinalities.
It excludes payload values, raw frames, sequences, filenames, device identifiers
and location fields. Encrypted payload variation is left unavailable.
Structural summaries still require review before publication.

The tool intentionally derives no rate or loss estimate from sequence gaps:
these files do not establish per-route sequence-counter ownership or continuous
capture coverage. Transfer receipt time is also not a sensor clock.

Next discriminating evidence is a controlled installed/removed transceiver
comparison and source-backed layouts or a known-good read-only trace. More idle
frames alone cannot identify physical owners, distinguish fixed status from
inactive streams, or establish the unanswered device-info query's session rules.
