# PiBlindHub continuity

- Objective: replace the prototype with a safe, testable H24 control stack on `full_refactoring`.
- Completion: all software safety invariants, API truthfulness, persistent recovery, systemd packaging, docs, tests, audit, commit, push, and remote SHA verification pass.
- Plan: [.codex/plans/full-refactoring.md](plans/full-refactoring.md)
- Decision: one minimal GPIO-owning control daemon; Web/API communicate only over a local Unix socket.
- Decision: no automatic movement or calibration at startup; interrupted motion restores an unknown position.
- Decision: physical interlock, fusing, relay rating, and independent cutoff are documented deployment gates, not software claims.
- Status: implementation and all local verification complete; publication pending.
- Next: commit, push `full_refactoring`, and verify the remote SHA and clean worktree.
- Blocker: exact relay/optocoupler schematic and motor model remain required before physical deployment, but do not block software-safe defaults.
- Verification: 61 passed, 1 Windows-only IPC skip, 82.89% coverage; lint, types, build, shell/JS/JSON/YAML, wheel smoke, diff, and Gitleaks pass.
