# Reproducible USB descriptor comparison

The comparison tools prepare evidence for a later DEP1 installed/removed/restored
experiment. No physical handling is required for software validation. A comparison
of two unchanged current inventories tests the tools, not transceiver ownership.

## Cached inventory

From the repository directory, build with the existing compiler and libusb:

```sh
python3 tools/build_helper.py --target usb_descriptors
python3 diagnostics/usb_inventory.py capture --output /path/to/current-inventory.json
```

The command runs `build/usb_descriptors --all-dji` with no shell or stdin. It
uses cached descriptor APIs, with no explicit device open, interface claim,
standard control request, bulk transfer or configuration change. It does not
compete with the orientation viewer for endpoint `0x85`. No software is installed.
The filter includes every product ID under DJI VID `2ca3`; an alternate DJI
PID is therefore retained. The orientation reader itself remains restricted
to its verified device/interface layout.

Saved fields include VID/PID, USB revision fields, device class, configuration
descriptors, interface/alternate descriptors and endpoint descriptors. Fields
are normalized and sorted before comparison. Product/serial strings, raw string
contents, bus/device addresses, hostname and unrelated vendors are omitted.
Temporary bus/address churn therefore does not appear as an interface change.

`bcd_device` is a USB descriptor revision field, not verified aircraft firmware.
Configuration descriptors list available layouts, not the active configuration.
Power and interval fields retain descriptor values without guessing units from
an unsupported bus speed or transfer-type assumption. No endpoint traffic or
physical component identity is inferred from descriptor contents.

If the target is not visible or the backend fails, the result is inconclusive.
This can reflect sandbox/backend restrictions. An unavailable observation is
never compared as if the transceiver or aircraft had disappeared. Use the same
command in a normal Terminal if needed; no sudo, driver install or firmware
change is part of this workflow.

## Future controlled comparison

Only label a physical state that the operator has actually established:

```sh
python3 diagnostics/usb_inventory.py capture --module-state installed --power-state on --output /path/to/installed.json
python3 diagnostics/usb_inventory.py capture --module-state removed --power-state on --output /path/to/removed.json
python3 diagnostics/usb_inventory.py capture --module-state installed --power-state on --output /path/to/restored.json
python3 diagnostics/usb_inventory.py compare /path/to/installed.json /path/to/removed.json --output /path/to/installed-removed.json
python3 diagnostics/usb_inventory.py compare /path/to/installed.json /path/to/restored.json --output /path/to/installed-restored.json
```

These are example commands for **separate physical states**, not a script that
changes the hardware. Module installation/removal must occur fully powered off
with USB disconnected according to DJI's procedure. Do not hot-swap. Use the
appropriate aircraft USB port, same Mac/cable and equivalent power state;
record port changes separately. See [transceiver evidence](transceiver-evidence.md).

The tool reports descriptor equality and field changes. It recognizes a reported
installed/removed pair only when power labels are known/equal, host environment
and helper hash match, and exactly one device is present per observation.
Unknown conditions and multiple devices remain ambiguous. These annotations
are operator reports; the software cannot independently verify the handling,
cable/port choice or physical unit identity without collecting further evidence.

A difference is a lead to test after restoration, not proof of chipset or
logical-host ownership. Matching descriptors do not prove DEP1 is unused.
Packet routing must be compared separately using receive-only observations and
the [offline profiler](passive-packet-findings.md). Do not use descriptor
similarity to justify trying arbitrary commands.

## Software validation on 6 November 2026

Two unchanged cached observations produced identical normalized structures:
one `2ca3:0020` device, USB descriptor `bcdDevice=0504`, configuration descriptor
1 with eight interfaces and the same five vendor bulk pairs. Physical labels
were deliberately unknown; no installed/removed claim was produced. The live
viewer continued streaming with zero DJI application-command bytes sent.
Synthetic tests cover endpoint differences, ordering, alternate DJI product IDs,
privacy filtering, unavailable observations, and mismatched physical/host/helper
conditions. This verifies the diagnostic workflow, not the physical experiment.
