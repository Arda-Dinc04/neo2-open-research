# DEP1 transceiver evidence — 6 November 2026

**No reviewed primary source maps a separate USB function, chipset, or DUML
host route to DEP1.** The module's exact product identity and radio role are
documented. The observed aircraft USB/DUML paths must not yet be attributed
to a particular transceiver processor.

## Exact DEP1 evidence

| Source | Established fact | Does not establish |
| --- | --- | --- |
| DJI Neo 2 specifications | Wi-Fi is the standard video path; the optional Digital Transceiver supplies O4. Aircraft Wi-Fi/Bluetooth are separately listed. | A Mac-compatible O4 adapter API or a USB endpoint map |
| DJI Neo 2 manual and connection guide | The module is installed for supported controller/goggles use. The installed module's external USB-C port can connect the aircraft to a computer. It must not be hot-swapped. | Whether USB is forwarded, multiplexed or terminated by a particular chip |
| Manufacturer-filed UL RF report | Product name is DJI Neo 2 Digital Transceiver, model **DEP1**, FCC ID **SS3-DEP125**. The report covers a radio test arrangement involving the module and aircraft. | A general computer control protocol or component-to-host-address mapping |

Sources: [DJI specifications](https://www.dji.com/se/neo-2/specs?set_region=SE),
[DJI manual](https://dl.djicdn.com/downloads/DJI_Neo_2/UM/20251210/DJI_Neo_2_User_Manual_v1.2_en.pdf),
[DJI connection guide](https://repair.dji.com/help/content?customId=01700043608&lang=en&paperDocType=ARTICLE&spaceId=17).

The exact filing document inspected is UL report **4791807217-2-RF-1**, issued
27 June 2025 for SZ DJI Technology. Its printed page 9 describes DEP1's 2.4 GHz
radio test parameters and 5 V DC supply. Pages 13–14 distinguish aircraft
Wi-Fi/BLE transmissions from the radio-under-test arrangement and list a
USB-C cable, laptop, and DEN225 aircraft as supporting equipment. The setup
mentions laptop-operated engineering RF test software. This is evidence of a
test arrangement, not instructions or authorization to enter that mode; no
such action was attempted. It provides no USB interface numbers, descriptors,
command framing, chipset identifiers or DUML addresses.
[Manufacturer-filed RF report, hosted mirror](https://fccid.io/m/7caccaaad6bec618c8553f821288c9f284a62e11b2bfb9cb87f6a745a109b267.pdf).

`DEP125` is the FCC identifier's product-code suffix; the report itself calls
the model `DEP1`. Do not silently rename the hardware model from the suffix.

## Internal-photo evidence and remaining access limits

Internal-photo exhibit **8482209** was subsequently retrieved and visually
inspected. Its seven-page PDF has SHA-256
`2e813bb5748e6f706e7bc0ee84cd6de91c65df5a05d06809db367f8d5a994cc9`.
Page 2 shows a removable USB-C connector PCB and a separate shielded main
board in the module housing. Page 7 shows the board with shielding removed,
but thermal material obscures the large package marking. No processor/radio
part number or USB bridge function was verified. Visible board separation
does not establish the electrical signal path, endpoint ownership or DUML route.
[Manufacturer-filed internal photos, hosted mirror](https://fccid.io/m/2e813bb5748e6f706e7bc0ee84cd6de91c65df5a05d06809db367f8d5a994cc9.pdf).

Block diagram, schematic and BOM entries remain metadata-only in the reviewed
index. This is an access limit, not evidence that those documents or an
internal USB connection do not exist. [Filing/exhibit locator](https://fccid.io/SS3-DEP125).

Other DJI aircraft, goggles, O4 products or logical-host enum names can supply
search leads. They cannot assign a Neo 2/DEP1 function by analogy. In
particular, address `48` remains a logical type/instance observed in aircraft
traffic; it is **not identified as the DEP1 modem**. The public record reviewed
here also does not demonstrate standalone Mac use of the detached module.

## Next non-destructive mapping experiment

After the present orientation bench session, collect a controlled comparison:

1. Record a receive-only inventory and short idle capture with the module
   installed, noting aircraft power state and software revision.
2. Power the aircraft fully off and disconnect USB. Remove the module only
   using the manufacturer procedure; do not hot-swap or open the module case.
3. Repeat the same inventory and idle observation through the aircraft's
   appropriate direct port, using the same Mac/cable and equivalent power state.
4. Restore the installed configuration while fully powered off, then repeat
   once to check whether any change is reproducible.

Compare enumerated devices, configuration/interface descriptors, endpoints,
logical hosts, command pairs and stream counts. A host/interface disappearing
with the module would establish a correlation to investigate, not chip
ownership by itself. An unchanged composite descriptor would not show that
the module is unused. Do not probe other command IDs, enter RF test modes,
or change firmware to make this comparison.

The [cached inventory and offline comparison tools](usb-comparison.md) implement
the descriptor portion and preserve unknown physical conditions. Current
unchanged-observation checks verify the software, not installed/removed behavior.

This source-only investigation performed no hardware operations and sent no
drone requests. The full component map remains in [components.md](components.md).
