# macOS USB driver bindings

Observed 6 November 2026 with the receive-only viewer running. This diagnostic
reads the existing IOService registry; it performs no USB endpoint, network,
DHCP, ping, discovery, driver-installation or configuration operations.
It establishes host attachment at that time, not firmware capabilities.

## Observed result

One DJI `2ca3:0020` device had registry active-configuration value 1 and eight
interface objects. The registered-network-interface query was nonempty, so
correlation was available. No registered network-interface object was a
descendant of the DJI device or either RNDIS interface.

| Interface | Descriptor class/subclass/protocol | Observed descendant services |
| --- | --- | --- |
| 0, RNDIS control | `e0/01/03` | None |
| 1, RNDIS data | `0a/00/00` | None |
| 2, storage | `08/06/50` | USB mass-storage, SCSI, block-storage and media classes |
| 3, vendor | `ff/43/01` | None |
| 4, vendor | `ff/43/01` | `AppleUSBHostInterfaceUserClient`, while the viewer owned the receive interface |
| 5–7, vendor | `ff/43/01` | None |

The descriptor-advertised RNDIS function currently has no attached child
services in this tree and no correlated host network interface. Therefore no
working USB network path was established on this Mac. This is not a general
claim that macOS can never use the function, nor that the aircraft exposes no
network services. No IP address, route or TCP/UDP service was guessed or probed.
No driver was installed to change this state.

Storage attachment and the independent vendor receive path are already usable;
they do not require a working RNDIS binding. This observation does not explain
USB host-to-device forwarding rules or establish a device-info session.

## Reproduce

```sh
python3 diagnostics/macos_usb_bindings.py --output /path/to/new-bindings.json
```

The script queries `IOUSBHostDevice` and `IONetworkInterface` with macOS's
`ioreg` utility. It correlates registry IDs in memory, then exports only logical
USB IDs, interface descriptor fields, driver class names and counts. Serial and
product strings, registry IDs, MAC/IP addresses, BSD interface names and process
identities are omitted. No raw registry dump is saved. It requires no libusb
interface claim and can run alongside the viewer.

Interface/driver nodes can inherit `idVendor` and `idProduct`. Only the USB query
roots count as devices; recursively counting inherited vendor properties would
mistake this aircraft's interfaces and storage services for additional aircraft.
Duplicate root IDs are deduplicated internally without exporting those IDs.

If `ioreg` is denied by a sandbox, the script reports an observation failure;
the same command can be run in a normal Terminal. A failed query or missing DJI
root does not establish physical absence. An empty global network registry
leaves network correlation unavailable, represented by null counts. The two
queries are sequential snapshots, so a concurrent driver change can require
repeating the observation; this is not an atomic USB trace.

The [cached descriptor comparison](usb-comparison.md) and
[passive route profiles](passive-packet-findings.md) answer different questions.
No correspondence between a host driver class, DUML logical host, physical
processor or DEP1 chipset is established here.
