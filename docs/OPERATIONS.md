# Operations

## Service status

```bash
systemctl status piblindhub-control piblindhub-api
journalctl -u piblindhub-control -u piblindhub-api --since today
curl --fail http://127.0.0.1:8080/health
```

The health endpoint is public but reveals only whether the control daemon is healthy.
Detailed status and events require the bearer token.

## Start and stop order

Start control before adapters. Stop adapters before control:

```bash
sudo systemctl start piblindhub-control piblindhub-api
sudo systemctl stop piblindhub-mqtt piblindhub-api piblindhub-control
```

A graceful control stop requests both outputs inactive, verifies readback, persists the
estimated or unknown position, then cleans up GPIO.

## Backup and restore

Back up `/etc/piblindhub` and `/var/lib/piblindhub/state.db` only while the control service
is stopped. These files are private and must not be committed. Restoring a database whose
movement marker is active intentionally produces an unknown position and no movement.

## Update and rollback

1. Remove motor power or ensure a person can use the hardware stop.
2. Stop all three services.
3. Back up private configuration/state.
4. Install the reviewed commit into `/opt/piblindhub/venv`.
5. Re-run disconnected-output checks before powered movement.

Never roll back only the database schema independently of the executable. A rollback must
restore the matching environment and database backup together.

## Fault handling

Do not repeatedly reset a fault. Remove motor power, inspect the event log and wiring, and
confirm inactive output readback. A reset leaves position unknown and never moves the blind.

If `output_readback_confirmed` is false, treat output state as unknown even if both displayed
booleans are false. Use the independent hardware stop and inspect locally.

## Log retention and monitoring

Logs go to journald. Configure host retention appropriate for the SD card. Alert on:

- service restart loops;
- systemd watchdog failures;
- `fault` or `safety_timeout` events;
- an unhealthy `/health` result;
- missing MQTT availability when MQTT is enabled.

Perform a physical stop, interlock, timeout, and power-recovery test at least annually and
after any wiring, OS, relay, motor, or software change.
