# Domain context

An aircraft USB **device** can contain several USB **interfaces**. Each bulk
interface has IN/OUT **endpoints**, where direction is relative to the Mac.
The native viewer reads only interface 4's IN endpoint 0x85.

DUML **hosts** are logical routing identities inside packets, encoded as a
five-bit type and three-bit instance. A host address does not name a physical
chip or establish ownership by the detachable transceiver.

The **aircraft channel** currently decodes source 03, command 03/43, using a
recognized 85-byte layout. One exploratory bench cycle supports candidate
fields A=pitch, B=roll, C=yaw, positive for nose-up, right-side-down and clockwise
rotation from above. Hand-estimated tilts and sparse samples do not establish
scale accuracy or repeatability. See docs/first-bench-findings.md.

The **gimbal channel** decodes source 04, command 04/05, using a recognized
50-byte layout. SDK pitch/roll/yaw fields and quaternion structure have been
inspected; physical conventions, stabilization frame and camera alignment
remain separate questions.

**Receipt time** is PC monotonic time at ingestion. It is not a sensor timestamp
or camera exposure time. Each channel independently ages stale.

A **bench marker** records an operator's physical action and observed angles.
It never commands the drone and never automatically grants calibrated status.
**View zero** is a browser display reference, independent from raw values and
bench comparisons.

The **DEP1 digital transceiver** supplies the aircraft-side O4 path documented
by DJI. Its presence does not establish a standalone Mac radio adapter. No
specific USB interface or DUML host is yet assigned to it.

The future **video adapter** provides attributed image observations from the
separate camera process. Its transport/session/recording lifecycle is not owned
by the orientation viewer. No exposure-time pose alignment is established.
