# Recorded-media metadata and live HEVC fields

Reviewed 7 November 2026. This source and saved-file review performed no device
I/O and changed no camera code. Camera-session, decoding and recording work
remain owned by the separate video workstream.

## External recorded-media parser evidence

The pinned [ExifTool DJI module](https://github.com/exiftool/exiftool/blob/9b8664dfcf2c609d3cc8925d380e98ad2a379f9b/lib/Image/ExifTool/DJI.pm)
recognizes `dvtm_NEO2.proto` in `djmd`/`dbgi` timed metadata. Its Neo 2 mappings
largely inherit Neo 1 entries, including frame information, a timestamp,
exposure fields, `DroneInfo` angles and GPS. A Neo 2 override initializes GPS
coordinate units to degrees. Its [maintainer](https://github.com/exiftool/exiftool/issues/440#issuecomment-6426220827)
describes this as basic support based on Neo 1.

Those are parser mappings, not locally validated Neo 2 sensor conventions.
The generic `GimbalInfo` table is not a dedicated Neo 2 gimbal mapping in the
reviewed inheritance path. A field named `DroneInfo` also does not establish
the physical reference frame. Timestamp origin and exposure alignment remain
unverified. Do not reuse recorded-media coordinate conversions or timestamp
scaling for FC DUML fields or live HEVC vendor data.

No original onboard MP4 was inspected here, and ExifTool was not installed or
run. No external sample media was downloaded. An existing unmodified original
MP4 would be needed to test this separate path locally; this review requested
no onboard recording.

## Our four retained live-stream files

The [previously reviewed Wi-Fi windows](wifi-route-findings.md) retained four
nonempty `camera.hevc` files. Bounded ffprobe inspection identified each as
an HEVC elementary stream with one HEVC video stream. This establishes the
retained format, not complete-file decoding or absence of embedded SEI data.
These files are not MP4 containers carrying separate `djmd`/`dbgi` tracks.
Remuxing them alone is not evidence of recovering those source metadata tracks.

An offline run of the pinned [byte-clock inventory](https://github.com/smichea/dji-neo2-lan-client/blob/014e3ad0d3ee98fecba94dfa48fe512a217a155f/src/neo2_control/video_clock.py)
gave the following results. It was used as a strict source-byte inspector,
without starting the camera or changing the video process.

| Window | Retained bytes | Raw first-slice candidates | Paired SEI candidates | Matching encoded-interval checksums | Inspector SEI parse failures |
| --- | --- | --- | --- | --- | --- |
| W1 | 1,338,333 | 407 | 407 | 407 | 1 |
| W2 | 22,764,198 | 1,362 | 1,362 | 1,362 | 167 |
| W3 | 73,673,170 | Unavailable | Unavailable | Unavailable | Unavailable |
| W4 | 359,206,127 | 13,960 | 13,960 | 13,960 | 1,731 |

Parse-failure counts describe this inspector, not measured lost frames or
camera faults. Successful container probes are not full-file decode checks.

The recognized pairs contain SEI payload type 240/size 25 and type 256/size 92.
Across the three accepted files, all 15,729 available checksums matched the
inspected original encoded intervals; none used the zero-checksum bypass.
This supports the source's byte-interval association, not decoded-frame
identity, a physical clock unit, latency or camera exposure time.

First-slice counts are not displayed/decoded frame counts. For example, W2 and
W4 had respectively 1,329 and 13,855 candidates after the parser's parameter
bootstrap condition, while the raw counts above include earlier candidates.
Count agreement with earlier preview results alone is not frame lineage proof.

W3 was rejected with `video_clock_multilayer_not_supported`. Its inventory
counts remain null rather than zero. This is the strict inspector's boundary;
it does not prove true multilayer encoding, missing vendor metadata, the cause
of a playback problem, or a spontaneous session dropout. No guard was bypassed
and no candidate time was promoted from that file. Parser investigation belongs
with the video workstream.

## Integration consequence

Keep three evidence domains distinct: PC receipt/decode time, live HEVC vendor
fields, and onboard MP4 timed metadata. The latter's supported field names and
conversion rules do not identify the former's semantics. Byte association is
also weaker than exposure-time alignment.

The [frame boundary](integration.md) therefore retains
`camera_timestamp: null` and `camera_clock_verified: false`. A future adapter
may retain raw vendor clock candidates with their source layout and a separate
producer clock-domain label; it must leave unknown units unavailable. It must
not silently convert them into exposure-time poses or use protobuf defaults
to fabricate an unavailable physical observation.

## Reproduce and preserve evidence

For a local retained file, the container probe is read-only:

```sh
ffprobe -v error -probesize 1048576 -analyzeduration 1000000 -show_entries format=format_name:stream=index,codec_name,codec_type -of json /path/to/private-camera.hevc
```

The pinned video's `inventory_hevc_clocks(path)` is a file-only inspector;
its full report contains raw metadata bytes, clock candidates and a source
digest. Keep that report private. Do not suppress its errors or substitute
zero counts when it rejects an input. No raw metadata or user image data is
included in this repository.

Focused upstream verification produced 29 passing tests and one failing CLI
test: that path imports the optional `spatial_capture` package, absent from the
existing Mac environment. The direct file reader used here does not require
that CLI path. No dependency was installed, no CLI fix is claimed, and the
separate camera source remains unchanged. This result does not establish a
fully working upstream CLI installation.

The [reviewed aggregate](media-metadata-summary.json) contains counts and
explicit unknowns only. [Source provenance](media-source-provenance.json)
records the reviewed parser versions and limits. Source hashes and original
media stay in the local private evidence record. Optical delay and physical
pose/reference validation remain deferred.
