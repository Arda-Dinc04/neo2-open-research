# Sources and attribution

The included host tools and analysis implementations were created for this
investigation. This bundle contains no DJI firmware/software binaries and no
copies of the reviewed upstream GPL source files.

- `o-gs/dji-firmware-tools` (GPL): reference for DUML bit packing, legacy command
  names and USB selection conventions. Those labels do not prove Neo 2 support.
  https://github.com/o-gs/dji-firmware-tools
- `smichea/dji-neo2-lan-client` (MIT): source evidence for the receive-only USB
  idle baseline, provisional gimbal/FC/battery field layouts, SWUDP envelope
  and WLM forwarding wire structure. The offline Wi-Fi census is an original
  receive-file implementation informed by those definitions. Pinned revision:
  `014e3ad0d3ee98fecba94dfa48fe512a217a155f`.
  https://github.com/smichea/dji-neo2-lan-client
- The 17-byte synthetic framing vector in `tests/test_duml_observer.py` is
  attributed to that MIT project's `tests/test_duml.py`; it is never transmitted.
  It is a protocol test vector, not a device capture or flight validation.
- DJI manuals/specifications ground the distinction between aircraft Wi-Fi,
  installed DEP1/O4 hardware, and supported remote-controller/goggles use.
- External hardware sources are cited in `docs/hardware-source-provenance.json`.
  Teardown photographs/articles and manufacturer-filed source artifacts retain
  their original rights; this bundle contains links and original research notes,
  without redistributing those artifacts.

Source URLs and inspected blob identifiers are in
`docs/routing-source-provenance.json`. Referenced projects retain their own
licenses; incorporating actual third-party code later requires preserving the
applicable notices and license terms for that contribution.
