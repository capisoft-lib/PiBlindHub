# HTTP API

The gateway defaults to `http://127.0.0.1:8080`. All `/api/v1/*` routes require:

```text
Authorization: Bearer <high-entropy-token>
```

The server stores only the token SHA-256 digest. Generate a token with
`piblindhub-token`; the installer shows it once. API documentation endpoints and CORS are
disabled intentionally.

## Endpoints

- `GET /health` — minimal, unauthenticated control-loop health.
- `GET /api/v1/status` — controller state, output readback, position confidence, fault.
- `POST /api/v1/commands` — enqueue a validated command and return HTTP 202.
- `GET /api/v1/commands/{id}` — current in-memory command lifecycle.
- `GET /api/v1/events?limit=100` — recent persistent control events.

Command body examples:

```json
{"command":"move_up"}
```

```json
{"command":"stop"}
```

```json
{"command":"set_estimated_position","position":50.0}
```

Supported values are `move_up`, `move_down`, `stop`, `reset_fault`, and
`set_estimated_position`. `completed` for a movement command means the requested direction
was energized and confirmed by GPIO readback; it does not claim the blind reached an end
position. Poll status/events for later timeout or faults.

## Exposure rules

The process refuses a non-loopback bind without a TLS certificate/private-key pair. For LAN
access, prefer a maintained TLS reverse proxy with client access control and firewall rules.
Do not put the token in a query string, URL, log, source file, or public configuration.
