# External Neo 2 teardown findings

Reviewed 7 November 2026. These are externally reported physical findings,
not an inspection of the operator's aircraft or a mapping of logical hosts.

Yoji Shimizu of Techanalye published a first-hand teardown in
[EE Times Japan, 28 November 2025, page 3](https://eetimes.itmedia.co.jp/ee/articles/2511/27/news060_3.html).
Figure 9 provides the following evidence:

| Item | Narrow finding | Remaining question |
| --- | --- | --- |
| GNSS package | Marking reads `UC6580I` | Same part/revision on this operator's unit; board connection and firmware access |
| Communications package | Legible `AIC8800M80` prefix; full ordering suffix unverified | Electrical bus, radio roles and relationship to received traffic |
| Processor | Author reports a new DJI processor; photograph does not establish an exact part | Part number, architecture, firmware ownership and physical-to-logical mapping |

The photograph identifies search leads for physical silicon. It does not
assign any of those packages to USB interface 4, logical source `48` or `92`,
or the detachable DEP1/O4 module. A package's position in a composite figure
does not establish its connector wiring or internal bus. The earlier FCC
photo's patch-like board remains a GNSS hypothesis; these separate photographs
do not prove that board's identity.

## Supplier cross-check

Unicore's [UC6580 product page](https://en.unicorecomm.com/products/dual-band-gps-chip-uc6580/)
lists `UC6580I` as an industrial-grade QFN40 member of its dual-frequency,
multi-constellation GNSS SoC family, integrating RF and baseband. This checks
the package-family interpretation, not a complete Neo 2 receiver design.
Supplier interface and protocol capabilities do not establish which connections,
enabled features or host APIs DJI uses. No NMEA stream, direct GNSS device,
antenna connection or usable receiver command path was observed here.

No supplier datasheet was verified for the full AIC package suffix. Do not
import distributor specifications or a related part's driver assumptions into
the capability matrix.

## Source disagreement

The figure labels Bluetooth 5.0; [DJI's model specification](https://www.dji.com/se/neo-2/specs?set_region=SE)
lists Bluetooth 5.2. Retain this difference rather than inferring the aircraft's
enabled Bluetooth features from the figure caption. Neither establishes a
generic Mac O4 adapter.

## Reproduce the source review

Open the article's figure-9 enlargement, then inspect the
[original public figure](https://image.itmedia.co.jp/ee/articles/2511/27/l_mm251127_tech09.jpg).
The reviewed JPEG's SHA-256 is
`8eafdf370e366a3e354ab321d361682511f8f9f47d3bb8204b395f1e6f4f1043`.
This digest identifies the inspected bytes; it does not guarantee an unchanged
future URL or any board revision. Copyrighted figures and article copies are
not included in this repository or source archive.

[Machine-readable source provenance](hardware-source-provenance.json) records
the scope and limits. A matching local board record or model-specific wiring
source is still needed before assigning physical ownership. A source-backed
packet layout and independent bench reference remain necessary for a new
sensor capability. No hardware was operated during this review.
