#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this uninstaller as root." >&2
  exit 1
fi

for unit in piblindhub-mqtt piblindhub-api piblindhub-control; do
  systemctl disable --now "${unit}.service" 2>/dev/null || true
  rm -f "/etc/systemd/system/${unit}.service"
done
systemctl daemon-reload

echo "Removed services and executables."
echo "Preserved /etc/piblindhub and /var/lib/piblindhub intentionally."
rm -rf /opt/piblindhub
