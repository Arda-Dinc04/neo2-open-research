# Additional Neo 2 USB host-source review

Reviewed 7 November 2026. Source inspection and saved-descriptor comparison
only; no external script was imported or executed, and no device was opened.

The [linnin233 Neo 2 tools project](https://github.com/linnin233/dji-neo2-tools/tree/f0b715ad5f064c25439e389cb892befa7c2e3cff)
claims Neo/Neo 2 USB support. This review pins revision
`f0b715ad5f064c25439e389cb892befa7c2e3cff`. An author's compatibility claim and
host implementation are source evidence, not an independently reproduced
Neo 2 request/response session or a firmware-side handler.

## Interface selection corroboration

The saved standard configuration-string descriptor, index 4, reads
`rndis,mass_storage,bulk,acm`. Configuration 1 contains eight interfaces.
The peer's [selection function](https://github.com/linnin233/dji-neo2-tools/blob/f0b715ad5f064c25439e389cb892befa7c2e3cff/comm_serialtalk.py#L135-L176)
has two relevant branches:

| Source branch | Result on the saved descriptors | Interpretation |
| --- | --- | --- |
| Configuration string available, comma-separated tokens | `acm` is token index 3; the source's index-plus-one rule chooses interface 4, OUT `0x04`, IN `0x85` | Corroborates the interface used by our observed telemetry and historical query |
| Configuration string unavailable, subclass fallback | All vendor interfaces 3–7 have subclass `43`; the first in the saved order is 3 | Subclass alone does not uniquely identify our observed interface |

The second row is a conditional source comparison, not a run of that client
on this Mac or proof it used interface 3 on another computer. Our standard
descriptor read did return the configuration string. Neither branch identifies
physical processor ownership or establishes host-originated request delivery.
The `acm` token does not turn the vendor-class descriptor into a demonstrated
CDC serial device. There is no reason from this review to change the viewer's
receive-only interface 4 selection.

## Request framing and read-path limits

The peer's [request helper](https://github.com/linnin233/dji-neo2-tools/blob/f0b715ad5f064c25439e389cb892befa7c2e3cff/comm_og_service_tool.py#L189-L218)
uses PC type, instance 0, ordinary unencrypted DUML requests, and caller-selected
target/command. The [bulk wrapper and sender](https://github.com/linnin233/dji-neo2-tools/blob/f0b715ad5f064c25439e389cb892befa7c2e3cff/comm_serialtalk.py#L105-L121)
write encoded packets directly to the selected OUT endpoint. This is not a
Neo 2 `00/ff` response demonstration. The saved historical request remains
`0a → 03`, flags `40`, command `00/ff`, empty payload, sent on interface 4.
No new request was constructed or transmitted by this review.

The model enum includes `NEO2`, but its parameter-get dispatch selects a
generic modern-platform routine. Both normal and alternate
[get paths call Assistant Unlock first](https://github.com/linnin233/dji-neo2-tools/blob/f0b715ad5f064c25439e389cb892befa7c2e3cff/comm_og_service_tool.py#L948-L999).
The [USB opener](https://github.com/linnin233/dji-neo2-tools/blob/f0b715ad5f064c25439e389cb892befa7c2e3cff/comm_serialtalk.py#L221-L267)
also attempts kernel-driver detachment, configuration selection and interface
claiming. A command named “get” therefore cannot be adopted as a receive-only
procedure under this project's restrictions. No unlock, driver change or
configuration selection was attempted, and the source does not establish that
any of these steps is required for our identity request.

Its reply matcher can ignore the response flag while still matching command,
reversed addresses and sequence. Our earlier [broad saved-RX audit](usb_routing.md)
already searched all flags and all addresses: no `00/ff` frame or query sequence
was found. Relaxing a response-flag check does not explain that absence.

## What remains unresolved

The source corroborates the string-based interface choice and exposes actions
hidden behind a read-oriented CLI name. It does not resolve `00/ff` support on
the Neo 2 FC host, forwarding/session policy, or physical endpoint ownership.
Changing sender instance, choosing another OUT endpoint, sending an unlock or
replaying Wi-Fi registration is not justified by this comparison.

A known-good, model/version-specific USB trace must record the exact interface,
endpoints, both directions, framing, target and any preceding setup, including
state-changing steps. Alternatively, a matching firmware-side handler could
establish support. That evidence must precede another device-info request.
Current receive-only visualization can continue independently when physical
testing resumes.

Exact inspected Git blob identifiers are in
[routing-source-provenance.json](routing-source-provenance.json). The source
project is GPLv3; this repository includes original review notes and links,
not copies of its code or executable parameter tools. Private descriptor/query
capture digests remain local.
