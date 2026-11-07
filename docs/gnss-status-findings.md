# GNSS status candidates in saved FC traffic

Reviewed 7 November 2026. This is offline analysis of saved aircraft traffic.
No new device session, request, configuration change or physical test occurred.

The pinned Neo 2 [FC decoder](https://github.com/smichea/dji-neo2-lan-client/blob/014e3ad0d3ee98fecba94dfa48fe512a217a155f/src/neo2_control/telemetry.py#L44-L65)
provides two field interpretations within the observed 85-byte `03/43` layout:

| Payload field | Source-backed candidate | Limit |
| --- | --- | --- |
| Byte 36, unsigned | Satellite count | Meaning, sentinel values and accuracy not independently verified |
| Little-endian 32-bit word at byte 32, mask `0x00008000` | `gps_valid` boolean | Not the complete SDK location-availability condition or proof of a usable fix |

The source uses additional flag bits, coordinate checks and an extension-field
case to decide location availability. The offline checker deliberately does not
decode that location or present a navigation-valid state. Its GNSS field reader
accesses only bytes 32–36; the coordinate block at bytes 0–15 is not unpacked
or exported. Framing/CRC validation still checks complete received packets.

## Observed saved windows

All accepted rows below are CRC-valid source `03`, command `03/43`, payload
length 85 and DUML flags `00`. U1–U3 are the three earlier saved USB windows;
W1–W4 are the [previously reviewed camera Wi-Fi windows](wifi-route-findings.md).
U2/U3 use receive bytes saved during the earlier identity-query investigation;
this analysis does not retransmit those requests.

| Window | Transport and recipient | FC occurrences | Satellite candidate byte | GPS bit set occurrences |
| --- | --- | --- | --- | --- |
| U1 | USB interface 4, `0a` | 17 | 0 throughout | 0 |
| U2 | USB interface 4, `0a` | 128 | 0 throughout | 0 |
| U3 | USB interface 4, `0a` | 98 | 0 throughout | 0 |
| W1 | Forwarded Wi-Fi, `0e` / `aa` | 215 / 31 | 0 throughout | 0 / 0 |
| W2 | Forwarded Wi-Fi, `0e` / `aa` | 469 / 94 | 0 throughout | 0 / 0 |
| W3 | Forwarded Wi-Fi, `0e` / `aa` | 1,001 / 198 | 0 throughout | 0 / 0 |
| W4 | Forwarded Wi-Fi, `0e` / `aa` | 4,744 / 957 | 0 throughout | 0 / 0 |

These are **243 USB and 7,709 Wi-Fi frame occurrences**, not unique physical
measurements. Recipients, flags, transport layer and USB interface remain
separate cohorts; repeated transport deliveries are not deduplicated. Saved
Wi-Fi input digests, complete header counts and routes matched the earlier
audit. Its ACK-mode-1, contained-frame, no-FEC/reassembly limitations still apply.

All-zero candidates provide no positive evidence of a position fix in these
windows. They do not prove receiver failure, absence of a GNSS chip, lack of
support outdoors, or that a particular firmware configuration caused the state.
No independently recorded satellite/fix indication or reception reference was
available for this comparison. No coordinate values or sky-view assumptions
are published. The external [UC6580I package finding](independent-teardown-findings.md)
does not establish ownership of this FC telemetry or direct receiver access.

## Reproduce offline

For an existing USB capture, the component inspector includes GNSS candidates
and a bounded route summary alongside its existing provisional fields:

```sh
python3 diagnostics/inspect_components.py /path/to/private-usb-capture.json --output /path/to/new-private-component-report.json
```

For a saved Wi-Fi capture, request GNSS status explicitly:

```sh
python3 diagnostics/audit_wifi_capture.py /path/to/private-swudp.jsonl --gnss-status --output /path/to/new-private-route-report.json
```

Without `--gnss-status`, the Wi-Fi auditor's output remains header/structural
only. With it, `gnss_status` contains counts, byte ranges and false verification
flags, never position bytes, coordinates or full controller flag words. The
profile retains at most 64 cohorts and a 256-bit distinct-byte set per cohort;
exceeding the cohort limit fails explicitly. Unknown USB interface metadata
remains null. Responses, encrypted packets, unknown lengths and wrong sources
cannot contribute as FC observations. The field reader retains byte 255 rather
than silently interpreting it as either a sentinel or a valid satellite count.

The [reviewed aggregate summary](gnss-status-summary.json) contains no private
input digests, capture paths, session/device/network identifiers or user media.
Keep raw captures and full per-capture audit reports local. Source and fixture
blob identifiers are in [source provenance](gnss-source-provenance.json).
Upstream synthetic getter evidence is source evidence, not an independently
reproduced native SDK run or a physical Neo 2 GNSS validation.

The next promotion requires an independent recorded fix/satellite indication
under documented reception conditions. This remains deferred physical work;
no firmware or receiver-configuration change is needed or authorized here.
