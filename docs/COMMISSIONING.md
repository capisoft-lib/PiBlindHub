# Commissioning procedure

Do not skip steps and do not commission remotely without someone at the blind and a
hardware means to remove motor power.

## 1. Offline inspection

- Complete every item in [Hardware safety](HARDWARE_SAFETY.md).
- Back up the previous calibration/configuration outside this public repository.
- Disable the legacy GPIO service and cron entries; confirm no other process owns pins 23,
  24, 25, or 27.
- Run `pytest`, `ruff check .`, and `python -m compileall -q src` on the release checkout.
- Install with `sudo ./deploy/install.sh`; do not start services yet.
- Review `/etc/piblindhub/config.json`, especially active levels, pins, neutral delay, and
  movement timeout.

## 2. Outputs disconnected from the motor

- Measure boot and shutdown: both commands must remain inactive.
- Exercise each direction and verify the truth table and output readback.
- Request a reversal and measure a neutral interval at least as long as configured.
- Hold both physical buttons and verify the controller enters `fault` with inactive outputs.
- Hold each button separately; movement must stop when it is released.
- Freeze or kill the API: the local control timeout must still stop the output.
- Freeze the control process: the independent hardware timer must stop the output.

## 3. First powered movement

- Set a short conservative `max_movement_seconds` below the measured safe limit.
- Start `piblindhub-control`, inspect status, then start `piblindhub-api`.
- Use hold-to-move in short pulses while another person watches the blind.
- Confirm UP/DOWN mapping, internal end stops, current, noise, and mechanical freedom.
- Measure full travel several times in both directions before setting
  `full_travel_seconds` and the final maximum runtime.

## 4. Recovery and acceptance

- Cut Raspberry power during UP and during DOWN. Restore power and prove there is no
  automatic movement and position reports `unknown`.
- Interrupt graceful service shutdown during movement and prove outputs are inactive.
- Disconnect network/MQTT and prove physical controls and timeout remain functional.
- Record the tested versions, measurements, configuration checksum, and responsible person.

Only then enable the services:

```bash
sudo systemctl enable --now piblindhub-control.service
sudo systemctl enable --now piblindhub-api.service
```

Enable `piblindhub-mqtt.service` only after MQTT TLS and credentials have been tested.
