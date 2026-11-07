# OpenNeo compact aircraft build brief

Status: design planning, 2026-11-07. No reference aircraft, validated bill of
materials (BOM), printable airframe or flight result is claimed by this brief.

## Intended result

Create an original, reproducible, Neo-like aircraft that someone can build from
published mechanical files, purchased electronics, a wiring diagram and open
software. The user's first-prototype requirement is **"Neo-like size from the
start"**. A larger development aircraft does not satisfy that requirement.

The finished build guide should make assembly repeatable: print the structural
frame and shell, install the specified components, wire the documented pins,
use a versioned firmware/configuration release and follow its validation
procedure. A flight controller is one component of that system; buying one
does not provide a stabilized camera, video link, position sensing or vision
autonomy automatically.

The existing stock-aircraft [research goal](research-goal.md) remains a reference
workstream. Understanding DJI components can inform requirements and comparison
tests, but the original aircraft must not depend on recovering every DJI
protocol or replacing firmware on the stock Neo 2. No compatibility with stock
DJI motors, batteries, gimbal, camera or DEP1 is established for this build.

## Size, scope and openness

| Requirement | Design interpretation and current limit |
| --- | --- |
| Compact from prototype one | Use the Neo 2 footprint as the initial packaging reference. Exact dimensional tolerances still need agreement. |
| Reference dimensions and mass | DJI lists 147 x 171 x 41 mm and 151 g without DEP1; 167 x 171 x 54 mm and 160 g with DEP1. These are stock reference values, not demonstrated OpenNeo specifications. |
| Printable mechanical design | Publish editable native CAD, STEP and STL/3MF, with material, print orientation, fasteners and assembly notes. Include the load-bearing frame and guards, not only a decorative cover. |
| Repairable integration | Specify component revisions, connectors, pin order, supply and signal voltages, mounting clearances and replaceable parts. |
| Camera and radio provision | Reserve their mass, power, cooling, antenna locations and volume before freezing the frame, even if installed in a later stage. |
| Neo-like capabilities | Add video, position sensing, stabilization and vision as separately demonstrated capabilities. Matching DJI endurance, camera quality or autonomous behavior is not yet established. |
| Current work | Documentation, source review and original design planning. No device writes, firmware changes, motor or flight commands are introduced. Physical tests remain deferred. |

Reference: [DJI Neo 2 specifications](https://www.dji.com/se/neo-2/specs?set_region=SE).

An open, reproducible integration can use commercially purchased boards while
publishing our own CAD, wiring and software. That is different from having
editable, openly licensed designs for every purchased PCB. Record firmware,
hardware-design and documentation licenses separately; access to a manual or
schematic alone does not establish permission to reproduce a board. Do not
label the complete aircraft fully open hardware until those dependencies have
been checked. License original mechanical/electrical designs explicitly when
they are created, separately from this repository's existing MIT host tools.

## Proposed component architecture

| Function | Initial design direction | Evidence needed before selection |
| --- | --- | --- |
| Attitude control and motor drive | Compact autopilot plus four ESC channels, preferably an integrated board to reduce wiring and volume | Exact board revision, supported firmware target, outline/connector clearance, mass, cooling and rail capacity |
| Propulsion and battery | Select motors, props, ESCs and pack as one matched system | Thrust/current data at the intended voltage and prop size; installed mass and geometry; current and thermal margins |
| Control and telemetry | Documented radio interface, with ExpressLRS as an open-source candidate | Matched air/ground hardware, supported protocol, antenna placement and independently validated loss-of-link behavior |
| Camera and video | Separately replaceable camera/encoder and air/ground transport | End-to-end bandwidth, power, mass, measured delay and a working Mac receive path |
| Camera stabilization | Reserve a mounting interface; evaluate fixed camera, electronic stabilization and mechanical gimbal separately | Space, mass, actuator/power needs and measured image behavior for the selected approach |
| Position sensing | Add sensors appropriate to the required environment, such as optical flow/range or GNSS | Exact driver support, lighting/surface limits and measured position behavior; an IMU alone does not establish position hold |
| Vision autonomy | Budget additional compute and sensors if required by the chosen algorithms | Demonstrated compute, power, cooling and sensor performance within the same compact envelope |
| Mac software | Reuse observation models, diagnostics and browser playback where applicable | A new adapter for the selected original-aircraft transport; stock DJI session code is not a generic camera driver |

[ExpressLRS](https://www.expresslrs.org/) is an open-source control-link candidate,
not proof of compatibility with the stock Neo 2 or a video transport. A control
link and a video link have different requirements. ArduPilot's
[companion-computer architecture](https://ardupilot.org/copter/docs/common-companion-computers.html)
shows one way to separate autopilot and higher-level processing; fitting that
processing in this aircraft remains a design question.

O4 replication is not a prerequisite for this reference design. DJI-compatible
video could be evaluated later as an optional closed module. An open video
backend must earn its place through the same size, power and latency checks;
neither a long-range link nor a particular range is promised here. The Mac can
start as a viewer and telemetry station. A future control application needs
its own authorization, validation and loss-of-link design; it is not added to
the receive-only research tools.

## Compact controller candidates: evidence, not a shopping list

| Candidate | Published facts | Unresolved tradeoff |
| --- | --- | --- |
| MicoAir743-AIO-35A | Manufacturer lists H743, integrated four-channel AM32 ESC, 36 x 36 x 8 mm outline, 25.5 x 25.5 mm mounting pattern, 10 g and 3-6S input. ArduPilot documents a corresponding board target. | The supply range constrains battery/motor selection. Actual revision, component clearances, thermal behavior and PCB design license are unverified. A mounting pattern is not the board outline. |
| Crazyflie Bolt 1.1 | Manufacturer lists 35 x 9 x 42 mm including connectors, 5.4 g bare PCBA / 7.8 g with battery cable, 1S-4S input, a Crazyflie firmware base and downloadable schematics. | Requires external ESCs and their wiring/space. Manufacturer labels it Early Access. Complete-system fit, required capabilities and hardware-design licensing need review. |

Sources: [MicoAir manual](https://micoair.com/en/docs/flight-controller/micoair743-aio-series/micoair743-aio-35a-manual),
[ArduPilot board documentation](https://ardupilot.org/copter/docs/common-MicoAir743-AIO.html),
[Bitcraze product documentation](https://www.bitcraze.io/products/crazyflie-bolt-1-1/).

These examples establish that compact controller options exist. They do not
establish that the complete proposed aircraft fits, has adequate thrust, or
matches the Neo's mass. Do not purchase either as a validated OpenNeo component
on the strength of this brief. Keep similarly named board revisions distinct.
The MicoAir and ArduPilot pages also differ on analog OSD support; resolve the
exact revision before relying on that feature.

## Budgets before the shell

Create one candidate BOM with actual part numbers and evidence for each entry.
Every entry needs quantity, installed mass including cables/fasteners, complete
dimensions and access clearances, supply voltage, typical/peak load, relevant
signal interfaces, firmware support, availability and license status. Record
unknown quantities as unknown, not zero. In particular, include:

- Frame, guards, cover, mounts, fasteners and vibration isolation.
- Four motors and props, controller/ESCs, pack, wiring and connectors.
- Camera, encoder, video radio, control receiver and all antennas.
- Sensor modules, optional gimbal/compute and their regulation/cooling needs.

Sum the installed mass and each supply rail's load, with explicit reserves.
Choose the all-up mass and endurance targets from that evidence; neither the
stock 151 g nor a guessed flight time is a validated requirement yet. Compare
motor/prop data against the complete aircraft mass rather than the bare frame.
Guard clearance, wiring, antenna spacing, battery retention and heat paths must
fit in the CAD assembly. Printing the final shell comes after those checks.

## Deliverables and order of work

| Step | Reviewable result | Completion condition |
| --- | --- | --- |
| 1. Parts and budgets | Two compact power-system/controller options, with a sourced BOM and mass/power/space comparison | At least one complete option fits the working envelope on paper, with all important unknowns exposed |
| 2. Packaging | Parametric CAD assembly and printable unpowered fit model | Selected physical components and connectors fit; camera/radio/sensor allocations remain available |
| 3. Electrical definition | Wiring/pin diagram and power/interface table for exact component revisions | Every connection has a documented pin, voltage, signal direction and load; source discrepancies resolved |
| 4. Reproducible software | Selected open firmware versions, build provenance, configuration and simulation evidence | Features and limitations documented against exact hardware; no synthetic result called a hardware validation |
| 5. Assembly and bench evidence | Printed frame, measured mass, fit photos and stationary component observations | Physical tests remain deferred; fit and telemetry alone do not establish flight readiness |
| 6. Reference release | CAD, BOM, wiring, software/configuration, assembly instructions and validation records under explicit licenses | Another builder can reproduce the demonstrated capabilities; unimplemented Neo-like features remain listed |

The immediate desk-work milestone is step 1: resolve the compact power system
and component budget before committing to a shell. Measured propulsion and
later flight validation would be separate future work, outside the present
no-motor/no-flight/no-firmware-command session.

The stock-aircraft USB viewer and camera fork retain their existing ownership
and constraints. This design brief changes the long-term destination; it does
not turn proprietary hardware observations into open PCB designs, or authorize
control commands against the stock aircraft.
