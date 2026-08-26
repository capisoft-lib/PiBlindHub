# Architecture and safety decisions

## Processes

`piblindhub-control` is the sole GPIO owner. It contains a single actor-style worker that
serializes physical input, remote commands, reversal delays, timeout checks, output
readback, persistence, and systemd watchdog heartbeats.

`piblindhub-api` serves the static Web UI and authenticated REST endpoints. It can only
reach control through `/run/piblindhub/control.sock`. The socket is mode `0660` and shared
through the `piblindhub-ipc` group.

`piblindhub-mqtt` is optional and follows the same boundary. It accepts a deliberately
small command vocabulary and publishes acknowledgements separately from controller status.

## Controller states

```text
BOOT_SAFE -> IDLE -> MOVING_UP / MOVING_DOWN
                 \-> STOP -> REVERSING -> opposite direction
any state -------------------------------> FAULT
any state -- service termination --------> SHUTDOWN
```

`STOP` has the highest command priority. It cancels the pending reversal and all previously
queued commands so stale requests cannot restart the motor afterward. Physical movement has
the next priority. Timers are evaluated only after the next queued command, so a queued
stop cancels a pending direction before it can be energized.

## Persistence and crash recovery

SQLite uses synchronous transactions. A movement marker is committed before a GPIO drive
request. It is cleared only after a confirmed stop. If power or the process disappears in
between, the next start forces both logical outputs inactive and stores position as
`unknown`; it never resumes movement.

A controller fault is latched in SQLite across service and host restarts. Restarting the Pi
cannot be used as an implicit reset. Only `reset_fault`, while buttons are released and both
outputs are confirmed inactive, clears it; position remains unknown.

The event log contains operational facts, not credentials. Command results are bounded in
memory; persistent events are the audit trail.

## Trust boundaries

- Network clients are untrusted and bearer-authenticated at the gateway.
- The public UI stores its token in browser `sessionStorage`, not a cookie or URL.
- The API is loopback-only unless TLS is configured.
- Local Unix-socket access is restricted by OS users/groups.
- Only the control service belongs to the Raspberry `gpio` group.
- Examples contain no secrets; MQTT passwords are read from a named environment variable.

## Explicit non-guarantees

Python, Linux, systemd, and GPIO software cannot guarantee de-energization after a welded
relay, Pi lockup, broken output stage, wiring error, or loss of the supply used for logic.
The electrical interlock and independent timeout are therefore part of the safety design,
not optional enhancements.
