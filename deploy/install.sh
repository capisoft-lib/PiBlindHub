#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this installer as root." >&2
  exit 1
fi

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_DIR="/opt/piblindhub"
CONFIG_DIR="/etc/piblindhub"
ENV_FILE="${CONFIG_DIR}/piblindhub.env"

if [[ ! -r /proc/device-tree/model ]] || ! grep -qi "raspberry pi" /proc/device-tree/model; then
  echo "This installer only supports Raspberry Pi OS hosts." >&2
  exit 1
fi

if ! getent group gpio >/dev/null; then
  echo "Required Raspberry Pi 'gpio' group is missing." >&2
  exit 1
fi

getent group piblindhub-ipc >/dev/null || groupadd --system piblindhub-ipc
if ! id -u piblindhub-control >/dev/null 2>&1; then
  useradd --system --gid piblindhub-ipc --groups gpio --home-dir /nonexistent \
    --shell /usr/sbin/nologin piblindhub-control
fi
if ! id -u piblindhub-web >/dev/null 2>&1; then
  useradd --system --gid piblindhub-ipc --home-dir /nonexistent \
    --shell /usr/sbin/nologin piblindhub-web
fi
usermod --append --groups gpio piblindhub-control

install -d -m 0755 -o root -g root "${INSTALL_DIR}"
python3 -m venv "${INSTALL_DIR}/venv"
"${INSTALL_DIR}/venv/bin/python" -m pip install --upgrade pip
"${INSTALL_DIR}/venv/bin/python" -m pip install "${SOURCE_DIR}[raspberry,mqtt]"

install -d -m 0750 -o root -g piblindhub-ipc "${CONFIG_DIR}"
if [[ ! -e "${CONFIG_DIR}/config.json" ]]; then
  install -m 0640 -o root -g piblindhub-ipc \
    "${SOURCE_DIR}/deploy/config.example.json" "${CONFIG_DIR}/config.json"
  echo "Created ${CONFIG_DIR}/config.json; verify every GPIO and timing value."
fi

if [[ ! -e "${ENV_FILE}" ]]; then
  token_json="$("${INSTALL_DIR}/venv/bin/piblindhub-token" --json)"
  token="$(printf '%s' "${token_json}" | "${INSTALL_DIR}/venv/bin/python" -c \
    'import json,sys; print(json.load(sys.stdin)["token"])')"
  token_hash="$(printf '%s' "${token_json}" | "${INSTALL_DIR}/venv/bin/python" -c \
    'import json,sys; print(json.load(sys.stdin)["sha256"])')"
  printf 'PIBLINDHUB_API_TOKEN_SHA256=%s\n' "${token_hash}" > "${ENV_FILE}"
  chown root:piblindhub-ipc "${ENV_FILE}"
  chmod 0640 "${ENV_FILE}"
  echo "API token (shown once; store it in a password manager): ${token}"
else
  echo "Preserved existing ${ENV_FILE}."
fi

for unit in piblindhub-control piblindhub-api piblindhub-mqtt; do
  install -m 0644 -o root -g root "${SOURCE_DIR}/deploy/systemd/${unit}.service" \
    "/etc/systemd/system/${unit}.service"
done
systemctl daemon-reload

echo "Installation completed without enabling or starting motor control."
echo "Read docs/HARDWARE_SAFETY.md and complete docs/COMMISSIONING.md first."
