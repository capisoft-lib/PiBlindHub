# PiBlindHub

PiBlindHub is an open-source Raspberry Pi controller for one motorised blind using an
isolated, polarity-reversing two-wire interface. The project is designed around safe
failure: Web, MQTT, or process faults must not leave a direction output energized.

> **Commissioning status:** the software safety architecture is implemented and tested
> with fake GPIO. It must not drive a real blind until the electrical circuit, relay truth
> table, independent cutoff, timings, and emergency stop have passed the commissioning
> procedure.

## Safety model

- One small control daemon exclusively owns GPIO.
- Both directions can never be requested together.
- Every reversal is `STOP -> neutral delay -> other direction`.
- `STOP` has queue priority and cancels a pending reversal.
- Physical hold-to-move buttons override remote movement.
- A local monotonic timeout cuts outputs without relying on the Web or MQTT services.
- Startup, shutdown, signals, exceptions, and GPIO faults request both outputs inactive.
- GPIO output readback is exposed separately from the requested state.
- An interrupted movement restores `UNKNOWN`; the daemon never moves automatically at boot.
- Sensorless positions are explicitly labelled `estimated`.

Software is only one protection layer. Normally-open relays, electrical interlocking,
correct fusing/contact ratings, galvanic isolation, and an independent hardware timeout are
deployment requirements. See [Hardware safety](docs/HARDWARE_SAFETY.md).

## Architecture

```text
Browser/API client       MQTT broker
        |                     |
        v                     v
 piblindhub-api       piblindhub-mqtt       (no GPIO access)
        |                     |
        +------ Unix socket --+
                  |
                  v
       piblindhub-control                (only GPIO owner)
        | actor + timeout + SQLite |
        +-----------+-------------+
                    v
          relay/optocoupler interface
```

The API and MQTT adapters only enqueue commands through a local Unix socket. Removing or
crashing either adapter does not remove the local movement timeout or physical controls.
Details are in [Architecture](docs/ARCHITECTURE.md).

## Development

PiBlindHub requires Python 3.9 or newer.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev,mqtt]'
pytest
ruff check .
```

The tests use fake hardware and never energize GPIO. A Raspberry installation uses:

```bash
sudo ./deploy/install.sh
```

The installer deliberately does **not** enable or start motor control. Continue with
[Commissioning](docs/COMMISSIONING.md), then [Operations](docs/OPERATIONS.md).

## API and UI

The gateway binds to `127.0.0.1:8080` by default and requires a high-entropy bearer token.
It refuses cleartext non-loopback exposure. Put it behind a trusted TLS reverse proxy or
configure TLS before LAN access. See [API](docs/API.md).

MQTT is optional, disabled by default, uses TLS by default, and accepts only `move_up`,
`move_down`, and `stop`. It never imports a GPIO library.

## Public project

PiBlindHub is published at <https://github.com/capisoft-lib/PiBlindHub> under the
[MIT License](LICENSE). Never commit runtime databases, logs, credentials, device-specific
network data, tokens, private certificates, or an active `/etc/piblindhub` configuration.
