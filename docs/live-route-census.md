# Passive live route census

The viewer now keeps a bounded header-only census inside its existing receive
pipeline. It opens no additional USB handle and sends no application requests.
Every CRC-valid frame delivered to the reader contributes before payload
interpretation, including unknown commands, responses and encrypted frames.
Angle decoding retains its separate source/layout/flag rules.

Read the local census while the viewer is running:

```sh
curl --fail --silent http://127.0.0.1:8765/api/routes
```

`GET /api/routes` returns the `neo2.route-census.v1` schema with:

- Source mode: `live`, `replay` or `demo`, preserved in standalone exports.
- A session-local opaque observer ID, reset whenever the process restarts.
- Total CRC-valid frame count and elapsed host observation time.
- Routes grouped by sender, receiver, command set/ID, flags and payload length.
- Per-route count, first receipt uptime and latest receipt age.
- Route retention limit and explicit omitted-frame count.

The default retains 128 distinct route profiles. Once full, existing profiles
continue counting and frames on additional profiles increment the omitted
counter; no retained entry is silently evicted. `retained_counts_complete`
becomes false. Represented route counts plus omitted-frame count equal total
CRC-valid frames. This bounds memory and API size even with varying headers.

The endpoint exports no payload values, geographic fields, packet sequences,
serials, application token or bench observations. Full state remains at
`/api/state`; that endpoint includes the viewer's session token and angle data,
so use the dedicated route endpoint for a structural census export.

## Interpretation limits

Mode identifies source provenance. Counts are cumulative, and receipt ages
continue increasing when data stops. Check `/api/state` for the source lifecycle
and each orientation channel's freshness. Receiving an unknown command cannot
refresh or validate aircraft/gimbal angles.

Counts cover only frames delivered to this reader during this observer
session. USB buffering, transfer batching and time before observation affect
the window. Receipt times are host times; no sensor sampling frequency or
sequence-loss estimate is inferred. A new route profile can be a new recipient,
flag combination or payload length without implying a newly accessed component.
Logical addresses remain separate from physical chips or DEP1 ownership.

For comparisons, preserve the observer ID and source mode, and verify that
counts are complete. Do not subtract counters across process restarts or mix
live and synthetic exports. Store local snapshots outside the source tree;
publish reviewed aggregates. Compare the six previously observed idle routes
in [passive packet findings](passive-packet-findings.md), while leaving new
payload semantics unknown until independently supported.

This census can reveal the arrival of `03/55` battery or other previously
unseen message types without sending a request. It does not subscribe to,
activate or decode those streams. An absent message describes only the
observed receive window and does not establish the required session setup.

## Observed unchanged-setup window

Two live exports from the same observer on 6 November 2026 enclosed 105.235
seconds of host observation and 1,790 additional CRC-valid frames. All six
profiles were already present at the first export; zero frames were omitted.
The viewer remained streaming and sent zero DJI application-command bytes.

| Sender → receiver | Command | Flags | Payload bytes | Frames in window |
| --- | --- | --- | --- | --- |
| `03 → 0a` | `03/43` | `00` | 85 | 211 |
| `04 → 2a` | `04/05` | `00` | 50 | 1,053 |
| `04 → 2a` | `00/f1` | `00` | 8 | 105 |
| `04 → 8a` | `00/f1` | `00` | 8 | 105 |
| `48 → 2a` | `00/82` | `40` | 64 | 105 |
| `92 → 2a` | `03/ce` | `00` | 28 | 211 |

These arrival counts reproduce the earlier idle baseline on the current setup.
No `03/55` battery, `00/ff` identity or `00/99` subscription-agent message arrived
in this window. No request was sent to provoke one, so this does not test
response support or identify a session prerequisite. Physical power/module
states were unchanged for software observation; no new physical comparison or
angle reference was established.
