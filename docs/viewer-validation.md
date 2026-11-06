# Live viewer validation — 6 November 2026

The viewer was built and run on the user's Apple Silicon Mac with the aircraft
powered on and the transceiver reported installed. Fresh USB discovery showed
the same eight-interface `2ca3:0020` composite device. No separate DEP1 USB device
was identified; ownership of logical hosts remains unresolved.

The continuous source opened interface 4 and received IN `0x85` data. Live API
and browser checks showed aircraft `03/43` and gimbal `04/05` readings, advancing
frame counts, independent fresh ages, and `application_bytes_sent: 0`. The
browser rendered both instruments and traces without console errors. The
web API includes no raw packet payload or per-device serial.

This verifies receive/decode/display. The operator completed one exploratory
bench cycle; [results and limits](first-bench-findings.md) support candidate
axis directions without certifying scale accuracy or repeatability. Absolute
heading, camera alignment, sensor clocks and flight readiness remain unverified.

At this milestone, 54 tests passed, including isolated loopback HTTP tests
with synthetic state. Native code builds with `-Wall -Wextra -Werror`.
Replay/demo cannot record physical-validation markers; corrupt frames cannot
refresh angles; local annotations do not become drone commands. Offline analysis
recomputes wrap-safe comparisons and never marks a single cycle calibrated.
The next-run recorder requires three samples spanning at least one second in
a two-second window, addressing the sparse aircraft samples in the first run.
Offline structural profiling additionally checks capture boundaries, encrypted
data handling and omission of payload contents; see the passive packet findings.

No flight, firmware, driver-detach, reset, or application configuration commands
were used by this viewer. The private historical identity-query tool is absent
from this public source tree.
