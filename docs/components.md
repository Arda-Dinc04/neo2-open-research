# Neo 2 component map

This map separates received bytes, source-backed field interpretations, and
physical component ownership. It describes the research evidence gathered so
far, not a complete hardware reverse engineering or a flight SDK.

The operator reports the digital transceiver installed for this session. A
fresh inventory showed the same eight-interface aircraft composite device;
no separate DEP1 USB device was identified. A powered-off installed/removed
comparison remains necessary to investigate ownership. See
[transceiver source evidence](transceiver-evidence.md).

| Component or path | Evidence | Current capability | Unknown / next evidence |
| --- | --- | --- | --- |
| Aircraft USB composite device | Physical unplug/replug tied the observed `2ca3:0020` device to the aircraft; configuration 1 exposed eight interfaces | Enumeration, standard descriptors, device/interface inventory | Compatibility across versions and installation states |
| Vendor interface 4 | Powered-on IN `0x85` produced CRC-valid DUML; paired OUT descriptor is `0x04`; 1,790 more frames reproduced six idle routes in a 105.235-second live window | Receive-only stream, provenance, bounded live header census, offline profiles and bench annotations | Host-originated request forwarding/session rules and newly arriving component-specific messages |
| Vendor interfaces 3, 5, 6, 7 | Claim/read/release succeeded; short idle windows were silent | Descriptor inventory | Application functions and physical owners; silence does not prove unused |
| Flight-controller logical host | `03 → 0a`, command `03/43`, 85-byte payloads; one exploratory body-motion cycle | Candidate A=pitch, B=roll, C=yaw and positive directions documented in [first bench findings](first-bench-findings.md) | Repeated measured axis/scale checks, reference frame, timing and calibration |
| Gimbal logical host | `04 → 2a`, command `04/05`, 50-byte payloads; DJI specifies a two-axis tilt/roll mechanism | Provisional angle/quaternion fields and bounded [same-packet bench evidence retention](gimbal-paired-evidence.md); prior received norms near 1 | New retention is software-tested; physical repeat tests remain deferred. SDK yaw is not proof of a third motor; quaternion convention, stabilization frame and camera alignment remain unknown |
| Main-board storage package | Manufacturer-filed aircraft photo page 7 visibly marks a package BIWIN / 3D NAND | Photo-supported brand/type marking only | Exact part number/capacity, bus and firmware/media ownership; this operator's board has not been inspected |
| Air-side processor logical role | Address `48` (legacy type `8`, instance `2`) emitted `WA020` in `00/82` | Raw route/module-string observation | Physical chip, board, processor ownership, and meaning of the string |
| Vision-related logical role | Address `92` (legacy type `18`, instance `4`) emitted constant 28-byte `03/ce` payloads in two idle windows | Structural profile and route census | Legacy command label is forbid-data information; Neo 2 payload meaning and physical sensors remain unknown; no range or LiDAR access established |
| Source-92 Wi-Fi traffic | Four saved camera windows contain constant `03/ce` (28 bytes) and `24/71` (7 bytes) sent to `02` and `1c`, with equal content sets | Bounded [value-free structural profiles](vision-route-structure.md); no distance or health decoding | Model-specific seven-byte handler and independent physical reference; `24/08` birdview layout does not apply |
| Physical vision / proximity sensors | DJI declares omnidirectional monocular vision, downward infrared and forward LiDAR; public internal photos show optical subassemblies | Manufacturer specifications and physical photo inventory only | Sensor silicon, internal buses, source-backed measurement messages and independent units/range checks |
| Gimbal-origin component-state candidate | `04 → 2a` and `04 → 8a`, eight-byte `00/f1` payloads; equal payload sets in each idle window | Logical fan-out observation; legacy component-state label | Eight-byte layout, health semantics and receiver ownership; legacy sender-09 radio bit labels do not apply directly |
| Battery | No `03/55` packet in 2,065 inspected receive frames; legacy OSD byte-40 percentage mapping contradicted by 143/243 values above 100 | No validated battery API; rejected-layout evidence recorded | Actual USB packet route/layout and comparison against an independent indication |
| Battery over the camera Wi-Fi path | Four saved camera sessions contain forwarded `03 → 02` and `03 → 0e` pushes, `03/55`, payload length 10 | Header/layout observation and source-backed percentage candidate; [cross-transport findings](wifi-route-findings.md) | Independent battery indication, calibration and live observation-adapter validation; this does not establish USB availability |
| Camera and media storage | Mounted storage exposed generic `DCIM` / `MISC`; separate Mac Wi-Fi workstream demonstrated startup with Fly closed and USB host disconnected | Follow-up preview: 478.925 seconds, 13,855 encoded frames, 359,206,127 video bytes, retained 960 × 540 JPEG; operator stopped it | Exposure timing, camera/body transform, reconnect and production recording remain unvalidated; media stays private |
| Aircraft Wi-Fi / BLE | Mac CoreBluetooth verified FFF0/FFF4/FFF5; approved credential reads, network/DHCP verification and WLM service switching succeeded | Mac-only startup and 7:59 follow-up; cleanup passed; narrow discovery-expiry coordinator bug regression-tested | App labeled operator stop as network error; spontaneous dropout or forward receive-window overrun not demonstrated; concurrent USB/video remains unverified; setup is separately approved active work |
| Attitude/gimbal observations over camera Wi-Fi | Offline audit of 352,066 saved RX datagrams found forwarded FC `03/43` length 85 and gimbal `04/05` length 50 during four video sessions | Same command/length candidates carried without aircraft USB; reproducible [offline route audit](wifi-route-findings.md) | Current live adapter, measured axes and exposure-time alignment; logical routes do not identify physical chips |
| Digital Transceiver DEP1 / O4 | DJI documents compatible controller/goggles operation; internal photos show a separate USB-C connector PCB and shielded main board; installed state is operator-reported | Physical connection documentation and board inventory | Chipset and electrical USB path, separate USB identity, logical host, component telemetry, generic Mac radio API, ground-side bridge |
| RNDIS interfaces 0–1 | Control/data descriptors present; observed macOS registry showed no attached child services or correlated network interface | Descriptor and host-binding inventory; no working USB network path established on this Mac | Firmware-side services, alternative host binding, and network/session behavior; no addresses or services probed |
| Storage interface 2 | Mass-storage driver and filesystem path observed | Existing OS-mediated reads | Other storage/service functions; no partition or firmware access attempted |

Logical DUML host bytes encode `type = byte & 0x1f` and
`instance = byte >> 5`. Thus `0a`, `2a`, and `8a` are three PC-type instances,
not three identified physical computers. A legacy enum name is evidence about
a protocol label, not proof of a chip or detachable module. None of the
observed addresses has been assigned specifically to DEP1.

The single earlier General `00/ff` identity request was transferred over USB
but received no matching response. A broad search across 2,065 CRC-valid
received frames found neither a `00/ff` packet at any address nor the query's
sequence. A USB transfer completion does not establish application acceptance,
control authority, or an operational command path.

## Evidence required to promote a capability

Use these labels in code, UI and contributions:

- **Observed:** device state, descriptors or CRC-valid bytes were received.
- **Source-backed interpretation:** a cited implementation explains a field,
  with the applicable packet layout and raw bytes retained privately.
- **Bench-validated:** an independent, recorded physical reference confirms
  an axis/sign/scale under stated conditions, with repetitions and limits.
- **Unknown:** no suitable observation, layout or independent validation.

Do not promote a field to bench-validated from plausible values alone. A unit
quaternion norm does not establish quaternion convention. Decode success does
not establish flight readiness. Unknown values remain unavailable rather than
being replaced with zero.

## Sources

- [Local routing findings](usb_routing.md) and [source provenance](routing-source-provenance.json).
- [Passive packet structure](passive-packet-findings.md) and [legacy-label provenance](packet-source-provenance.json).
- [Physical hardware photo map and manufacturer sensing specifications](hardware-photo-map.md).
- [macOS driver-binding observations](macos-driver-bindings.md).
- [Status candidates and rejected battery mapping](status-battery-findings.md).
- [Wi-Fi camera-session route comparison](wifi-route-findings.md) and [reviewed aggregate counts](wifi-route-summary.json).
- [Source-92 structural findings](vision-route-structure.md) and [value-free summary](vision-structure-summary.json).
- [Live header census and observed unchanged-setup window](live-route-census.md).
- [Pinned upstream USB census](https://github.com/smichea/dji-neo2-lan-client/blob/014e3ad0d3ee98fecba94dfa48fe512a217a155f/tools/capture_usb_duml.py).
- [Pinned gimbal decoder](https://github.com/smichea/dji-neo2-lan-client/blob/014e3ad0d3ee98fecba94dfa48fe512a217a155f/src/neo2_control/gimbal_telemetry.py) and [FC decoder](https://github.com/smichea/dji-neo2-lan-client/blob/014e3ad0d3ee98fecba94dfa48fe512a217a155f/src/neo2_control/telemetry.py).
- [DJI connection guide](https://repair.dji.com/help/content?customId=01700043608&lang=en&paperDocType=ARTICLE&spaceId=17) and [Neo 2 manual](https://dl.djicdn.com/downloads/DJI_Neo_2/UM/20251210/DJI_Neo_2_User_Manual_v1.2_en.pdf).
