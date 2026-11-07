# What the saved source-92 traffic establishes

Reviewed 7 November 2026, using the same four private Wi-Fi camera windows as
the [route census](wifi-route-findings.md). This is offline analysis of existing
traffic. No device request, subscription or sensor configuration was performed.

Logical sender `92` has a legacy vision-related host label. That name does not
identify a physical chip, camera, LiDAR or other sensor on this aircraft.

## Constant payloads and logical fan-out

| Command | Payload bytes | W1 occurrences at `02` / `1c` | W2 | W3 | W4 |
| --- | --- | --- | --- | --- | --- |
| `03/ce` | 28 | 42 / 42 | 91 / 91 | 194 / 194 | 917 / 917 |
| `24/71` | 7 | 110 / 110 | 234 / 234 | 500 / 500 | 2,373 / 2,372 |

For each command in each window, all bytes were constant, with one distinct
payload and no changed offsets. The two receiver routes had equal payload
sets. A separate private comparison also found one payload value per command
across the four windows. Raw values and payload hashes are not published.

The different W4 counts show why content equality must not be treated as
verified one-to-one packet pairing or identical delivery. These are logical
recipient routes, not two independently measured physical sensors.

These observations provide a reproducible idle baseline. They do not determine
which bytes are flags, distances, status, padding or sentinels; show that a
sensor is inactive; or establish a warning/health verdict. No controlled change
to an obstacle or independent sensor reference is associated with these files.

## Why the birdview decoder does not apply

The pinned upstream [birdview reconstruction](https://github.com/smichea/dji-neo2-lan-client/blob/014e3ad0d3ee98fecba94dfa48fe512a217a155f/src/neo2_control/obstacles.py)
handles command `24/08`, with an eight-byte prefix and a nonempty array of
two-byte entries: total length `8 + 2 × count`, at least ten bytes. The observed
`24/71` payload is seven bytes. It is a different command and cannot satisfy
that wire layout. The birdview reconstruction itself leaves physical units,
angular calibration and special values unconfirmed.

No reviewed Neo 2-specific handler establishes the seven-byte layout. The older
`03/ce` command name is likewise insufficient to decode its 28 bytes. Reusing
another command's getters or inventing a scale would not make either a distance
measurement. The current component map therefore retains both meanings as
unknown.

## Reproduce without publishing payloads

```sh
python3 diagnostics/audit_wifi_capture.py /path/to/private-swudp.jsonl --profile-host 92 --output /path/to/new-private-profile.json
```

`--profile-host` is a logical source byte in hex, not a query target. The tool
still only reads an existing file. It adds per-route byte cardinalities,
changed offsets and distinct-payload counts, retaining layer, receiver, flags
and length. Equal complete payload sets can establish a content fan-out
observation; the output never claims packet timing/pairing.

Profiles exclude encrypted payloads and export no raw values or payload hashes.
Memory is bounded to 64 header groups, 32,768 profiled byte positions and 128
retained distinct payload digests per group. Beyond the digest limit, the exact
distinct count becomes unavailable and a lower bound is reported; capped sets
cannot establish fan-out. Exceeding the group/position bounds fails rather than
silently omitting profiles. Structural variation does not identify units or
physical ownership.

The [reviewed structural summary](vision-structure-summary.json) contains only
the two commands above. Its cardinalities, counts and fan-out results matched
the independent existing `packet_profiles` implementation when both were fed
the same CRC-checked inner frames. The original data remains private. The
earlier USB `92 → 2a` `03/ce` baseline is documented in
[passive packet findings](passive-packet-findings.md); no USB/Wi-Fi physical
owner or content equivalence is inferred from matching header fields.

## Evidence still needed

Seek a Neo 2-specific receive handler or a known-good observation with an
independent physical reference before naming fields. A later bench comparison
may discriminate proposed meanings once supported by source; it should retain
raw paired observations and exact setup conditions. More unchanged idle frames
alone cannot resolve the field semantics or assign a physical component.
