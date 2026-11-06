# Working in neo2-open-research

This is the canonical open host-tool repository. Historical raw captures and
the private identity-query experiment live outside this source tree.

- Preserve receive-only operation. The viewer owns USB interface 4 IN 0x85;
  no flight, firmware, calibration, configuration, or arbitrary-packet API belongs
  here. Review any proposed device-side request separately against the user's
  current authorization and source evidence.
- Live, replay and demo are distinct provenance modes. Never substitute a
  fixture for live hardware success or certify axes from decoder tests.
- Separate logical host addresses from physical chip/module identity. DEP1
  ownership remains unknown until supported by new evidence.
- Bench markers are local annotations; display zero is not device calibration.
  Keep both channel ages, raw-source fields and physical assumptions visible.
- Camera work is owned by the separate video workstream. See docs/video-goal.md
  and docs/integration.md. Do not modify its separate fork or claim its device
  interfaces as part of routine orientation-viewer work.
- Keep raw captures, device/account/network identifiers, session records, and
  user media out of Git and release archives. Use tools/package_release.py.
- Validate with `python3 -m unittest discover -s tests -v`, build the native
  helper with `python3 tools/build_helper.py`, and verify UI changes in a browser.
  Tests use synthetic state and must not operate hardware.
- Read CONTEXT.md and docs/components.md before changing field interpretations.
  Preserve source URLs/blob provenance and explicitly state remaining unknowns.
