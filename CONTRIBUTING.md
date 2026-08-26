# Contributing

PiBlindHub controls physical hardware. Describe the safety effect of any controller, GPIO,
timing, persistence, installer, or service change and include a deterministic test.

Before opening a pull request:

```bash
python -m pip install -e '.[dev,mqtt]'
ruff check .
ruff format --check .
mypy
pytest --cov=piblindhub --cov-fail-under=80
python -m build
```

Never test unreviewed changes on an unattended blind. Fake GPIO tests are required first;
real hardware tests must follow `docs/COMMISSIONING.md` with a physical power cutoff.

Public contributions must not contain credentials, private certificates, IP addresses,
device identifiers, runtime state, logs, or deployment-specific configuration.
