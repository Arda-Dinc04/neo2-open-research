# Radio frequencies and transceiver reference

Reviewed: 6 November 2026. This page records manufacturer-declared specifications;
it does not report measured RF output, a detected active channel, or demonstrated
radio interoperability.

## Sources and evidence

- **Supplied printed leaflet:** `IMG_7502.HEIC` and `IMG_7503.HEIC` show two views
  of the same DJI Neo 2 Digital Transceiver leaflet. The English specifications
  identify model **DEP1** and transmission system **O4**. A document revision is
  not legible in the supplied views. The photos are supporting source material,
  not two independent confirmations.
- **Official online cross-check:** [DJI Neo 2 specifications](https://www.dji.com/se/neo-2/specs?set_region=SE),
  sections “Video Transmission,” “Wi-Fi,” and “Bluetooth,” accessed 6 November
  2026. The O4 frequency/EIRP values agree with the photographed English table.
- **Manufacturer document reference:** [DJI Neo 2 Motion Fly More Combo Safety
  Guidelines v1.2](https://dl.djicdn.com/downloads/DJI_Neo_2/SG/20260112/DJI_Neo_2_Motion_Fly_More_Combo_Safety_Guidelines_v1.2.pdf).
  This is an additional published source, not an asserted revision of the
  photographed leaflet.
- The printed short link is `https://s.dji.com/neo2-transceiver`; its destination
  could not be retrieved during this documentation pass and was not used as
  evidence for additional facts.

The originals remain outside the repository. Only the relevant specification
facts and paraphrased notes are included here; no photo metadata is redistributed.

## DEP1 / O4: photographed specifications

Regional column names reproduce the leaflet's FCC, CE, SRRC, and MIC labels.
Every power value retains the printed **less-than** qualifier.

| Operating band, GHz | Equivalent span, MHz | FCC EIRP | CE EIRP | SRRC EIRP | MIC EIRP |
| --- | --- | --- | --- | --- | --- |
| 2.4000–2.4835 | 2400–2483.5 | <26 dBm | <20 dBm | <20 dBm | <20 dBm |
| 5.170–5.250 | 5170–5250 | Not listed | <23 dBm | Not listed | Not listed |
| 5.725–5.850 | 5725–5850 | <26 dBm | <14 dBm | <26 dBm | Not listed |

“Not listed” means that the photographed English table supplies no value for
that region/band combination. It is not an assertion of permission, prohibition,
or zero transmit power. The leaflet says band availability varies by country
and region. These published profiles do not establish which profile this
particular unit is currently using.

EIRP is equivalent isotropically radiated power, including antenna effects;
it is not a measurement of power at a USB connector or radio-chip output.
For scale, 14, 20, 23, and 26 dBm correspond to approximately 25, 100, 200,
and 398 mW respectively, using `mW = 10^(dBm/10)`. The table gives upper
bounds, not fixed operating power.

## Aircraft Wi-Fi and Bluetooth: separate online specifications

These values come from the official aircraft specification page, rather than
the transceiver leaflet. They should not be substituted for DEP1's O4 values.

| Link | Operating band, GHz | Published EIRP |
| --- | --- | --- |
| Wi-Fi, 802.11a/b/g/n/ac/ax | 2.400–2.4835 | <20 dBm (FCC/CE/SRRC/MIC) |
| Wi-Fi | 5.170–5.250 | <23 dBm (CE) |
| Wi-Fi | 5.725–5.850 | <26 dBm (FCC/SRRC); <14 dBm (CE) |
| Bluetooth 5.2 | 2.400–2.4835 | <10 dBm |

DJI lists standard Wi-Fi video transmission and optional DEP1/O4, and specifies
up to 60 MHz communication bandwidth in the video-transmission section. That
maximum is a separate specification, not a measured current bandwidth or a
Bluetooth/Wi-Fi channel width. [Official specification source](https://www.dji.com/se/neo-2/specs?set_region=SE).

## Installation and USB notes from the photographed leaflet

The leaflet describes normal controller/smartphone/DJI Fly linking after
installing the module. It also states that the installed module's external
USB-C port can charge or connect the aircraft to a computer without removing
the transceiver. This supports the physical computer connection; it does not
document a standalone Mac O4-radio API.

Relevant manufacturer handling notes, paraphrased:

- The module does not support hot-swapping; secure it before aircraft power-on.
- Avoid stressing or bending the antenna.
- Use the screwdriver supplied with the aircraft for the mounting screws.
- The leaflet associates unsuccessful linking with checking screw security
  and restarting the aircraft.

Those are **reference instructions from the supplied document**. Adding this
page did not execute pairing, restart the aircraft, change a regional profile,
or send any device, flight, firmware, or radio commands.

## Research implications and remaining unknowns

The frequency spans are a reference for component mapping and future RF
observations. Sharing a band does not establish O4 compatibility with a
Wi-Fi adapter, a generic SDR, or another aircraft-side transceiver. No such
compatibility follows from these tables.

The project's USB observations and decoded logical host IDs remain separate
evidence. This leaflet does not map a USB interface or DUML host to DEP1.
Active center frequency, channel width, transmit power, regional profile,
ground-side radio requirements, and a standalone transceiver command interface
have not been measured or established by these photos.

For the broader component evidence and open questions, see
[component map](components.md) and [USB routing findings](usb_routing.md).
