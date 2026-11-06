# Physical hardware evidence map

Reviewed 6 November 2026. Manufacturer-filed internal photographs are a record
of the submitted equipment, not a teardown of this operator's individual unit.
No case was opened and no hardware was modified during this source review.
Photos remain outside the source release; the table links the public records.

## Aircraft DEN225

[Internal-photo exhibit 8481875](https://fccid.io/m/36a5dc6e4c8898f79e948e7666b850613e6a9cef3905af49c6f0dff80009dc48.pdf),
15 pages, from [FCC ID SS3-DEN225](https://fccid.io/SS3-DEN225).
SHA-256: `36a5dc6e4c8898f79e948e7666b850613e6a9cef3905af49c6f0dff80009dc48`.
Page references below are the printed page numbers.

| Pages | Visible observation | Limit |
| --- | --- | --- |
| 7 | Both sides of a populated main board; one package visibly marked BIWIN and 3D NAND | Exact memory part number/capacity and main processor identity unverified; no physical-to-DUML mapping |
| 3, 8–9, 11 | Camera and smaller optical assemblies photographed separately from the main board | Exact imager identities, electrical interfaces and DUML ownership unknown |
| 12–13 | A separate board with a patch-like element | GNSS function is a visual hypothesis, not a confirmed receiver/chip identification |
| 14–15 | Antenna views and labels | No internal USB/DUML routing follows from antenna placement |

These images support a physical board/subassembly inventory. They do not
identify which board runs the observed FC, gimbal, vision or air-processor
logical host, and cannot establish sensor data access.

## DEP1 transceiver

[Internal-photo exhibit 8482209](https://fccid.io/m/2e813bb5748e6f706e7bc0ee84cd6de91c65df5a05d06809db367f8d5a994cc9.pdf),
7 pages, from [FCC ID SS3-DEP125](https://fccid.io/SS3-DEP125).
SHA-256: `2e813bb5748e6f706e7bc0ee84cd6de91c65df5a05d06809db367f8d5a994cc9`.
Pages 2–3 show the USB-C connector PCB separated from the shielded main board.
Page 7 exposes that board, with the large package marking obscured by thermal
material. No chipset identity or standalone USB-radio API was established.
See [transceiver evidence](transceiver-evidence.md) for the RF report and
controlled installed/removed comparison.

## Manufacturer-declared sensing components

DJI's [Neo 2 sensing specification](https://www.dji.com/se/neo-2/specs?set_region=SE)
names omnidirectional monocular vision, downward infrared sensing and forward
LiDAR. It gives a forward LiDAR measurement range of 0.3–8 m for reflectivity
above 10%, and a 60° horizontal by 60° vertical field of view. These are
manufacturer specifications, not results
of this USB experiment. No LiDAR/range decoder or direct sensor API has been
verified; the constant `92 → 2a` `03/ce` payload must not be labeled distance
data on the basis of these specifications. Camera image-sensor part number,
IMU/barometer parts, vision compute silicon, internal buses and radio chipset
remain unknown.

The same specification names a 1/2-inch CMOS camera sensor and a mechanical
gimbal with tilt and roll axes. It does not identify the imager part number.
The received SDK yaw field must therefore not be assumed to represent a third
mechanical gimbal motor. A three-angle pose representation and a two-axis
mechanism are compatible; the telemetry reference frame remains unverified.

## Evidence needed next

Correlate a controlled installed/removed DEP1 comparison with inventory and
passive packet profiles. Seek a legible component marking, readable schematic
or manufacturer part document before naming silicon. Relate any sensor message
to a source-backed layout and an independent bench reference before exposing
physical units. A plausible value or legacy host name is insufficient.
