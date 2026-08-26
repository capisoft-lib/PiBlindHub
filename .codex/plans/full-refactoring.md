# PiBlindHub full refactoring plan

## Objective

Replace the prototype execution paths with one fail-safe, testable architecture suitable for continuous home operation, while keeping hardware deployment explicitly separate from software publication.

## Completion criteria

- One control process exclusively owns GPIO and enforces mutual exclusion, break-before-make direction changes, priority stop, physical-button priority, and an independent local movement timeout.
- Startup, shutdown, exceptions, stale recovery state, and process signals leave both logical outputs inactive and never trigger automatic movement.
- Position is unknown after interrupted motion and is always labelled estimated without a physical sensor.
- Web/API/MQTT-facing code cannot access GPIO directly and reports accepted, running, completed, and failed commands truthfully.
- Runtime state is transactional and persistent; public examples contain no active credentials or device-specific data.
- systemd units, safe installation, operational documentation, CI, unit/integration tests, static checks, and secret scanning are present.
- The branch passes verification, is committed, pushed, and the remote SHA is verified.

## Work packages

1. Architecture, safety ADR, configuration contract, and package metadata.
2. Domain model, hardware protocol, Raspberry and fake GPIO adapters, controller actor, and SQLite state.
3. Unix-socket control daemon, authenticated FastAPI gateway, and minimal same-origin UI.
4. systemd supervision, installer, operations and hardware documentation.
5. Tests, lint/type/import/package checks, repository/privacy audit, commit, and push.

## Material constraints

- Software cannot provide the required electrical interlock, relay-contact rating, fusing, or independent hardware cutoff; these remain installation gates.
- The deployed Raspberry is not changed by this branch work.
- The existing `.gitignore` addition for `.local/` is preserved.
