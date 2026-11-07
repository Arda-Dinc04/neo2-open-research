# Paired gimbal evidence in private bench records

The receive-only viewer now retains Euler and quaternion fields from the same
accepted gimbal packet when recording a bench marker. This addresses a gap in
the earlier exploratory session: its eight markers retained angle summaries,
but no paired quaternion samples. The new storage cannot reconstruct missing
samples from those historical markers.

This is a software evidence-retention improvement, checked with synthetic
packets and loopback HTTP tests on 7 November 2026. It is not a new physical
bench result. Physical testing remains deferred, and no device command or
additional USB handle was introduced.

## What is retained

The existing two-second angle-summary window still requires fresh live data
from both channels, at least three samples per channel spanning one second,
and records spread without automatically certifying an axis. Cohorts now retain
one logical source route and observer session rather than mixing sources.
Supported FC plaintext push ACK modes still belong to the same route.

Each full marker export can additionally contain
`gimbal_sample.paired_evidence`, schema `neo2.gimbal-paired-evidence.v1`:

- Original three signed little-endian Euler integers, their source-backed
  0.1-degree interpretation and the original six field bytes at payload offset 0.
- Original four little-endian float fields and their sixteen field bytes at
  payload offset 24, kept in the recorded SDK order. No reordering, averaging,
  sign alignment or normalization is applied.
- Quaternion norm as a structural observation, source sender/receiver,
  command, flags, sequence and payload length for each pair.
- PC monotonic receipt offsets relative to marker collection, one observer
  session identity, eligible/retained/omitted counts and retained time span.

Only these selected gimbal fields are retained. The export does not include
complete USB transfers, geographic position fields, unrelated gimbal bytes,
camera media or the browser annotation token. Framing and CRC were checked at
ingestion; selected field bytes alone cannot recheck the complete original CRC.
Any full original captures must be handled separately as private evidence.

The retained float values are checked against their original field bytes.
An invalid or missing quaternion cannot be replaced with the current quaternion
or fabricated from an angle summary. Finite field retention does not certify
that a quaternion is a valid calibrated physical rotation.

## Bounds and delivery

At most 128 paired samples are retained per marker, within the existing
200-marker session limit. If there are more eligible pairs, selection uses
uniform indices including the first and last sample. Omitted counts and the
retained span are explicit. This is a bounded evidence subset, not a complete
bus capture or a guarantee of uniform sensor-time sampling.

The polling state and annotation response expose counts/metadata only. The
individual pairs are included in **Export local annotations**, endpoint
`/api/bench/export.json`, and in the local session JSON file. Session files are
written atomically with mode 0600 under ignored `local-data/bench-sessions/`.
New session directories use mode 0700. Exported observations remain private;
the source release excludes these records.

The outer `neo2-open-research/bench/v1` format remains compatible with older
angle-only records. Missing paired data is unavailable, not zero-filled.
The offline analyzer structurally rechecks pairs against their bytes and
reports `gimbal_paired_evidence` counts. A polling summary lacks the individual
samples and is identified as requiring a full export. Declared counts are not
trusted in place of saved samples.

```sh
python3 diagnostics/analyze_bench.py /path/to/private-bench-session.json --reference estimated --output /path/to/new-private-analysis.json
```

This inventories paired evidence and performs the existing angle analysis.
The bounded regular-file reader accepts up to 64 MiB, covering a supported
200-marker session with 128 pairs per marker; analysis output is created with
mode 0600 and an existing output path is refused. The maximum-size synthetic
export used for the capacity check was about 24.2 MB. This is a software test,
not 200 physical bench observations.
It does not fit a quaternion convention or automatically validate axes.
Use `--reference measured` only when an independent angle reference was used.

## Interpretation limits and future validation

Receipt pairing removes a cross-packet timing ambiguity between these Euler
and quaternion fields. It does not establish sensor time, camera exposure time,
quaternion component order, handedness, Euler composition order, physical signs,
stabilization reference frame or camera/body alignment. A near-unit norm alone
is insufficient. A single stationary pose cannot resolve all conventions.

A later independently referenced bench session should retain varied poses and
returns using the existing manual procedure, with the gimbal free and untouched.
The aircraft body and stabilized gimbal need not follow the same angles. Keep
raw paired evidence, setup conditions and limitations; promote only claims
supported by those actual observations. The viewer continues to send zero DJI
application-command bytes.

The source layout remains the pinned
[gimbal reconstruction](https://github.com/smichea/dji-neo2-lan-client/blob/014e3ad0d3ee98fecba94dfa48fe512a217a155f/src/neo2_control/gimbal_telemetry.py),
blob `fd12e130ea29e3e92f2cccb3856e598e68c27c9f`, already recorded in
[routing provenance](routing-source-provenance.json). The SDK field names do
not independently establish a physical quaternion convention.
