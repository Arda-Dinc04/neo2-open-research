# Contributing evidence and tools

Start with [the research goal](docs/research-goal.md), [component matrix](docs/components.md)
and [domain context](CONTEXT.md). This repository contains original receive-only
host tools around stock hardware. The separate
[Mac camera fork](https://github.com/Arda-Dinc04/dji-neo2-lan-client/tree/codex/macos-camera-preview)
owns camera setup and playback. Open host tools do not make vendor firmware or
hardware designs open source.

Useful contributions include source-backed message layouts, physical component
identification, model-specific read-only routing evidence, synthetic parser
fixtures, operating-system compatibility reports and controlled axis tests.
For each claim, include the hardware/model and software revision where known,
installation and power state, transport/interface, reproducible procedure,
source links and uncertainty. Distinguish your own observations from upstream
reports, synthetic results and hypotheses. A logical host ID does not identify
a physical processor.

Keep credentials, per-device/account/network identifiers, raw captures, location
data, firmware binaries and camera media out of commits and public issues.
Describe aggregate observations or use purpose-built synthetic fixtures. Do not
post unreviewed traces as attachments. Synthetic data must be labeled clearly;
it cannot validate a real device or a physical angle.

The USB helper reads interface 4, IN 0x85, and has no application-command send
path. Contributions here must preserve receive-only operation and independent
freshness/provenance. No flight, firmware, calibration, configuration or arbitrary
packet API belongs in this observer. A future control project requires separate
scope, authorization and validation.

Run the hardware-free checks and package the source allowlist:

```sh
python3 -m unittest discover -s tests -v
python3 tools/package_release.py
```

On a Mac with the documented compiler and libusb development files, also build
the helper with `python3 tools/build_helper.py`. Building does not open the
aircraft. Actual USB/radio sessions and physical bench trials are separate
operator-run checks; tests and replays must not be presented as those trials.

Original contributions use the repository's MIT license. Preserve third-party
attribution and applicable licenses when incorporating code; public source
availability alone does not grant permission to relicense it.
