# PiBlindHub continuity

- Objective: replace the prototype with a safe, testable H24 control stack on `full_refactoring`.
- Completion: all software safety invariants, API truthfulness, persistent recovery, systemd packaging, docs, tests, audit, commit, push, and remote SHA verification pass.
- Plan: [.codex/plans/full-refactoring.md](plans/full-refactoring.md)
- Decision: one minimal GPIO-owning control daemon; Web/API communicate only over a local Unix socket.
- Decision: no automatic movement or calibration at startup; interrupted motion restores an unknown position.
- Decision: physical interlock, fusing, relay rating, and independent cutoff are documented deployment gates, not software claims.
- Status: refactoring implemented, verified, and published on `full_refactoring`.
- Next: complete the electrical checklist and commissioning procedure before any Raspberry deployment.
- Blocker: exact relay/optocoupler schematic and motor model remain required before physical deployment, but do not block software-safe defaults.
- Verification: local suite and GitHub CI/secret scan pass; remote SHA verified and worktree clean.
