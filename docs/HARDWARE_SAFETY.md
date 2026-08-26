# Hardware safety contract

## Reported current interface

The current prototype was described as Raspberry GPIO driving relays and optocouplers (the
exact order is still unverified) to produce `0 V`, `+24 V`, or `-24 V` across two motor
wires. GPIO 23 and 24 are configured as mutually exclusive logical directions. GPIO 25 and
27 are configured as physical direction inputs.

This description is **not yet a validated schematic**. Before connecting PiBlindHub, record
the module references, input polarity, supply voltages, relay contact arrangement, motor
reference, current, internal limit switches, and measured two-wire truth table.

Expected logical truth table, to verify with the motor disconnected:

| UP output | DOWN output | Required result |
|---:|---:|---|
| off | off | neutral / motor unpowered |
| on | off | one 24 V polarity |
| off | on | opposite 24 V polarity |
| on | on | physically impossible, even if software fails |

The wire polarity associated with opening or closing must be measured; do not infer it from
names in the software.

## Required electrical protections

- Motor power never comes from a GPIO pin.
- GPIO sees only a correctly rated, isolated logic input.
- Direction relays use normally-open contacts and break-before-make behavior.
- A hardwired interlock prevents both polarity paths from closing together.
- Relays/contactors are rated for the motor voltage, stall current, DC switching, and
  inductive load; provide the manufacturer-required suppression.
- Motor and control supplies have correctly selected fuses.
- An independent timer or safety relay removes direction commands after the maximum travel
  time even if Linux freezes.
- A reachable physical stop removes the command independently of the Web UI.
- Power-up and loss of GPIO control de-energize both directions.
- Any mains-voltage portion is built or validated by a qualified professional.

Software readback only reads GPIO logical levels. It does not prove relay contact position,
motor current, direction, movement, end-of-travel, or blind position. Auxiliary contacts,
current sensing, or position sensors are required for those claims.

## Measurements to attach to the installation record

1. Annotated schematic and clear enclosure photographs.
2. Part numbers and data sheets for relays, optocouplers, supplies, fuses, and motor.
3. Measured voltage for all four logical output combinations with motor disconnected.
4. Proof that forcing both control inputs cannot create a forbidden output.
5. Measured full travel in both directions and worst-case stall/current behavior.
6. Independent timeout test with the Pi control process deliberately frozen.
7. Power-cut tests during each direction, followed by a no-motion restart.
