# PiBlindHub repository guidance

## Project identity

- The project name is **PiBlindHub**.
- PiBlindHub is an open-source project licensed under the MIT License.
- The canonical repository is public: https://github.com/capisoft-lib/ok-go-pour-PiBlindHub
- Keep public documentation, examples, package metadata, and UI naming aligned with PiBlindHub.

## Public repository rules

- Treat every committed file and every Git revision as publicly accessible.
- Never commit credentials, API keys, JWT secrets, password hashes, Wi-Fi credentials, private certificates, device GUIDs, personal addresses, local IP addresses, runtime databases, backups, or logs.
- Commit only sanitized `*.example.*` configuration files. Keep active configuration files local and ignored.
- Do not change the GitHub repository to private or publish deployment-specific data unless the owner explicitly requests it.
- Preserve GPIO safety: motor directions must be mutually exclusive, stopping must drive both outputs low, and hardware-facing changes require fail-safe cleanup and timeout handling.

